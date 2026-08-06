# voice/tts_queue.py — Prioritized Speech Queue & Interrupt Manager for JARVIS MK37
"""
Thread-safe prioritized speech queue for TTS engines supporting barge-in interrupts,
cancellation, and priority dispatch (URGENT / NORMAL / BACKGROUND).
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Optional


class SpeechPriority(IntEnum):
    URGENT = 1     # System alarms, warnings, voice shortcuts
    NORMAL = 2     # ReAct answers & assistant speak responses
    BACKGROUND = 3 # Long background summaries


@dataclass(order=True)
class SpeechItem:
    priority: int
    text: str = field(compare=False)
    on_start: Optional[Callable] = field(default=None, compare=False)
    on_finish: Optional[Callable] = field(default=None, compare=False)
    timestamp: float = field(default_factory=time.time, compare=False)


class TTSQueueManager:
    """Manager for prioritized TTS speech dispatch with barge-in interruption."""

    def __init__(self, speak_handler: Optional[Callable[[str], None]] = None):
        self._queue = queue.PriorityQueue()
        self._speak_handler = speak_handler
        self._current_item: Optional[SpeechItem] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    def set_handler(self, handler: Callable[[str], None]):
        self._speak_handler = handler

    def enqueue(self, text: str, priority: SpeechPriority = SpeechPriority.NORMAL, on_start: Optional[Callable] = None, on_finish: Optional[Callable] = None):
        if not text.strip():
            return
        
        # If URGENT priority, interrupt any currently playing lower priority item
        if priority == SpeechPriority.URGENT and self._current_item and self._current_item.priority > SpeechPriority.URGENT:
            self.cancel_current()

        item = SpeechItem(priority=int(priority), text=text, on_start=on_start, on_finish=on_finish)
        self._queue.put(item)
        self._ensure_worker()

    def cancel_current(self):
        """Cancel current speech item and purge queued items (barge-in)."""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            self._current_item = None

    def _ensure_worker(self):
        with self._lock:
            if not self._running:
                self._running = True
                self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
                self._worker_thread.start()

    def _worker_loop(self):
        while self._running:
            try:
                item: SpeechItem = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

            self._current_item = item
            if item.on_start:
                try:
                    item.on_start()
                except Exception as e:
                    if 'logger' in globals() or 'logger' in locals():
                        logger.debug('Suppressed exception: %s', e)
                    else:
                        import logging
                        logging.getLogger(__name__).debug('Suppressed exception: %s', e)
            if self._speak_handler:
                try:
                    self._speak_handler(item.text)
                except Exception as e:
                    if 'logger' in globals() or 'logger' in locals():
                        logger.debug('Suppressed exception: %s', e)
                    else:
                        import logging
                        logging.getLogger(__name__).debug('Suppressed exception: %s', e)
            if item.on_finish:
                try:
                    item.on_finish()
                except Exception as e:
                    if 'logger' in globals() or 'logger' in locals():
                        logger.debug('Suppressed exception: %s', e)
                    else:
                        import logging
                        logging.getLogger(__name__).debug('Suppressed exception: %s', e)
            self._current_item = None
            self._queue.task_done()

    def stop(self):
        self._running = False
        self.cancel_current()
