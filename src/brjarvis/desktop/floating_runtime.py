"""Runtime boundary for the BRJARVIS floating widget.

The Qt surface should render this adapter's snapshot and emit user intents.  The
adapter owns authenticated HTTP calls, worker-thread execution, connector
health, and normalized state so the floating widget does not duplicate runtime
or API behavior.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

logger = logging.getLogger(__name__)

_FLOATING_STATES = {
    "IDLE",
    "LISTENING",
    "PROCESSING",
    "THINKING",
    "SPEAKING",
    "EXECUTING",
    "WAITING",
    "ERROR",
}


@dataclass(frozen=True)
class FloatingWidgetState:
    """Serializable state projection consumed by Qt and headless surfaces."""

    visibility: str = "visible"
    runtime: str = "unknown"
    assistant: str = "idle"
    audio: str = "inactive"
    task: str = "none"
    input: str = "idle"
    connectors: str = "unknown"
    message: str = "Awaiting command..."
    error: Optional[str] = None
    transcript: str = ""
    latest_response: str = ""
    voice: str = "unavailable"
    speaker: str = "inactive"
    workspace: str = "idle"
    workspace_url: str = ""
    task_id: str = ""
    recent_tasks: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    connectors_data: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    capabilities: Mapping[str, bool] = field(
        default_factory=lambda: {
            "voice": True,
            "voice_to_text": True,
            "speaker": True,
            "workspace_handoff": True,
            "task_control": False,
            "connectors": True,
            "tray": True,
            "graphical_display": True,
        }
    )

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["connectors_data"] = [dict(item) for item in self.connectors_data]
        data["capabilities"] = dict(self.capabilities)
        return data


class FloatingRuntimeAdapter:
    """Thread-safe runtime adapter for the floating widget.

    The adapter intentionally accepts an optional orchestrator so existing
    callers remain compatible.  If no orchestrator is injected it uses the
    canonical local HTTP endpoint as a compatibility fallback.
    """

    def __init__(
        self,
        orchestrator: Any = None,
        *,
        request_session: Any = None,
        config_root: Optional[Path] = None,
        http_timeout: float = 30.0,
        voice_trigger: Optional[Callable[[], Any]] = None,
        voice_controller: Any = None,
        speaker_controller: Any = None,
        workspace_opener: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self.orchestrator = orchestrator
        self._session = request_session
        self._config_root = config_root
        self._http_timeout = http_timeout
        self._voice_trigger = voice_trigger
        self._voice_controller = voice_controller
        self._speaker_controller = speaker_controller
        self._workspace_opener = workspace_opener
        self._lock = threading.RLock()
        self._connector_inflight = False
        default_capabilities = dict(FloatingWidgetState().capabilities)
        if voice_controller is None:
            try:
                from brjarvis.desktop.floating_voice import FloatingVoiceController

                voice_controller = FloatingVoiceController()
                self._voice_controller = voice_controller
            except Exception:
                voice_controller = None
        default_capabilities["voice"] = bool(voice_trigger is not None or voice_controller is not None and voice_controller.available)
        default_capabilities["voice_to_text"] = default_capabilities["voice"]
        default_capabilities["speaker"] = True
        self._state = FloatingWidgetState(capabilities=default_capabilities)
        self._subscribers: list[Callable[[FloatingWidgetState], None]] = []

    def subscribe(self, callback: Callable[[FloatingWidgetState], None]) -> Callable[[], None]:
        """Subscribe to state updates and return an unsubscribe callback."""
        with self._lock:
            self._subscribers.append(callback)
            snapshot = self._state
        try:
            callback(snapshot)
        except Exception:
            logger.exception("Floating state subscriber failed during initial delivery")

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    def snapshot(self) -> FloatingWidgetState:
        with self._lock:
            return self._state

    def update(self, **changes: Any) -> FloatingWidgetState:
        with self._lock:
            current = self._state
            if "connectors_data" in changes and changes["connectors_data"] is not None:
                changes["connectors_data"] = tuple(dict(item) for item in changes["connectors_data"])
            if "capabilities" in changes and changes["capabilities"] is not None:
                changes["capabilities"] = {**current.capabilities, **dict(changes["capabilities"])}
            self._state = replace(current, **changes)
            snapshot = self._state
            subscribers = tuple(self._subscribers)
        for callback in subscribers:
            try:
                callback(snapshot)
            except Exception:
                logger.exception("Floating state subscriber failed")
        return snapshot

    def attach_runtime(self, orchestrator: Any = None, voice_trigger: Optional[Callable[[], Any]] = None) -> FloatingWidgetState:
        """Attach expensive runtime services after the surface is already visible."""
        with self._lock:
            self.orchestrator = orchestrator
            self._voice_trigger = voice_trigger
        return self.update(
            runtime="embedded_online" if orchestrator is not None else "offline",
            capabilities={"voice": voice_trigger is not None or self._voice_controller is not None and self._voice_controller.available, "voice_to_text": self._voice_controller is not None and self._voice_controller.available},
            error=None,
        )

    def set_visibility(self, visibility: str) -> FloatingWidgetState:
        return self.update(visibility=str(visibility).lower())

    def set_runtime(self, runtime: str) -> FloatingWidgetState:
        return self.update(runtime=str(runtime).lower())

    def set_assistant_state(self, state: str, *, message: Optional[str] = None) -> FloatingWidgetState:
        normalized = str(state or "IDLE").upper()
        if normalized not in _FLOATING_STATES:
            normalized = "ERROR"
            message = message or f"Unknown assistant state: {state}"
        assistant = "processing" if normalized == "THINKING" else normalized.lower()
        return self.update(assistant=assistant, message=message if message is not None else self.snapshot().message)

    def set_audio_state(self, audio: str) -> FloatingWidgetState:
        return self.update(audio=str(audio).lower())

    def set_task_state(self, task: str, task_id: str = "") -> FloatingWidgetState:
        return self.update(task=str(task).lower(), task_id=str(task_id or ""))

    def refresh_recent_tasks(self) -> None:
        thread = threading.Thread(target=self._fetch_recent_tasks, daemon=True, name="floating-task-history")
        thread.start()

    def _fetch_recent_tasks(self) -> None:
        try:
            response = self._request("GET", "/api/agent/tasks?limit=6", timeout=5.0)
            if getattr(response, "raise_for_status", None):
                response.raise_for_status()
            payload = response.json()
            tasks = payload.get("tasks", []) if isinstance(payload, Mapping) else []
            safe_tasks = []
            for task in tasks[:6]:
                if isinstance(task, Mapping):
                    safe_tasks.append({
                        "task_id": str(task.get("task_id", "")),
                        "goal": str(task.get("goal") or task.get("user_request") or "Untitled task"),
                        "status": str(task.get("status", "")),
                        "updated_at": task.get("updated_at"),
                    })
            self.update(recent_tasks=safe_tasks)
        except Exception as exc:  # noqa: BLE001 - history is non-blocking
            logger.debug("Unable to load floating task history: %s", exc)

    def continue_task(self, task_id: str) -> None:
        task_key = str(task_id or "").strip()
        if not task_key:
            return
        thread = threading.Thread(target=self._load_task_for_continuation, args=(task_key,), daemon=True, name="floating-task-load")
        thread.start()

    def _load_task_for_continuation(self, task_id: str) -> None:
        try:
            response = self._request("GET", f"/api/agent/tasks/{task_id}", timeout=5.0)
            if getattr(response, "raise_for_status", None):
                response.raise_for_status()
            payload = response.json()
            goal = str(payload.get("goal") or payload.get("user_request") or "").strip()
            if not goal:
                raise RuntimeError("Previous task has no recoverable goal.")
            self.update(task_id=task_id, transcript=goal, task=str(payload.get("status", "loaded")).lower(), message="Previous task loaded. Review it and press Send to continue.", error=None)
        except Exception as exc:  # noqa: BLE001 - continuation is recoverable
            self.update(message="Previous task could not be loaded.", error=self._safe_error(exc))

    def set_connector_health(self, status: str, connectors: Optional[list[Mapping[str, Any]]] = None) -> FloatingWidgetState:
        return self.update(connectors=str(status).lower(), connectors_data=connectors or [])

    def submit_command(self, text: str) -> None:
        prompt = str(text or "").strip()
        if not prompt:
            return
        if self._voice_controller is not None and self._voice_controller.recording:
            self._voice_controller.stop()
        if self._speaker_controller is not None and self._speaker_controller.speaking:
            self._speaker_controller.stop()
        self.update(input="submitting", voice="ready", speaker="inactive", audio="inactive", assistant="processing", task="running", message=f"> {prompt}", error=None)
        thread = threading.Thread(target=self._run_command, args=(prompt,), daemon=True, name="floating-command")
        thread.start()

    def trigger_voice(self) -> None:
        if self._voice_trigger is not None:
            self.update(audio="recording", voice="recording", assistant="listening", message="Listening…")
            try:
                self._voice_trigger()
            except Exception as exc:  # noqa: BLE001 - callback boundary becomes user state
                logger.warning("Floating voice trigger failed: %s", exc)
                self.update(audio="unavailable", voice="error", assistant="error", error=self._safe_error(exc))
            return
        if self._voice_controller is None or not self.snapshot().capabilities.get("voice_to_text", False):
            self.update(audio="unavailable", voice="unavailable", assistant="error", error="Voice input is unavailable in this runtime.")
            return
        if self._voice_controller.recording:
            self.stop_voice_capture()
            return
        self.update(audio="recording", voice="recording", assistant="listening", message="Listening…", error=None)
        self._voice_controller.start(
            on_state=self._voice_state,
            on_transcript=self._voice_transcript,
            on_error=self._voice_error,
        )

    def stop_voice_capture(self) -> None:
        if self._voice_controller is not None:
            self._voice_controller.stop()
        self.update(audio="inactive", voice="ready", assistant="idle", message="Voice capture stopped.")

    def _voice_state(self, state: str, message: str) -> None:
        audio = "recording" if state == "recording" else "inactive"
        assistant = "listening" if state == "recording" else "processing" if state == "transcribing" else "idle"
        self.update(audio=audio, voice=state, assistant=assistant, message=message)

    def _voice_transcript(self, transcript: str) -> None:
        self.update(transcript=str(transcript).strip(), voice="ready", audio="inactive", assistant="idle", message="Transcript ready.", error=None)

    def _voice_error(self, message: str) -> None:
        self.update(voice="error", audio="inactive", assistant="error", error=str(message), message="Voice input needs attention.")

    def speak_latest_response(self) -> None:
        text = self.snapshot().latest_response or self.snapshot().message
        if self._speaker_controller is None:
            try:
                from brjarvis.desktop.floating_voice import FloatingSpeakerController

                self._speaker_controller = FloatingSpeakerController()
            except Exception as exc:
                self.update(speaker="unavailable", error=self._safe_error(exc))
                return
        if self._speaker_controller.speaking:
            self.stop_speaker()
            return
        self.update(speaker="synthesizing", audio="playing", message="Preparing short response…", error=None)
        self._speaker_controller.speak(text, on_state=self._speaker_state, on_error=self._speaker_error)

    def stop_speaker(self) -> None:
        if self._speaker_controller is not None:
            self._speaker_controller.stop()
        self.update(speaker="inactive", audio="inactive", message="Speaker stopped.")

    def _speaker_state(self, state: str, message: str) -> None:
        self.update(speaker=state, audio="playing" if state in {"synthesizing", "speaking"} else "inactive", assistant="speaking" if state == "speaking" else "idle", message=message)

    def _speaker_error(self, message: str) -> None:
        self.update(speaker="unavailable", audio="inactive", assistant="error", error=str(message), message="Speaker unavailable.")

    def request_workspace_handoff(self, on_ready: Optional[Callable[[str], Any]] = None) -> None:
        self.update(workspace="authenticating", message="Connecting workspace…", error=None)
        thread = threading.Thread(target=self._run_workspace_handoff, args=(on_ready,), daemon=True, name="floating-workspace-handoff")
        thread.start()

    def _run_workspace_handoff(self, on_ready: Optional[Callable[[str], Any]]) -> None:
        try:
            response = self._request("POST", "/api/auth/desktop-handoff", json={"redirect": "/web/"}, timeout=5.0)
            if getattr(response, "raise_for_status", None):
                response.raise_for_status()
            payload = response.json()
            url = str(payload.get("url") or "").strip()
            if not url:
                raise RuntimeError("Workspace handoff did not return a browser URL.")
            self.update(workspace="ready", workspace_url=url, message="Workspace ready.", error=None)
            if on_ready:
                on_ready(url)
        except Exception as exc:  # noqa: BLE001 - workspace failures become recoverable UI state
            logger.info("Workspace handoff failed: %s", exc)
            self.update(workspace="failed", message="Workspace connection failed.", error=self._safe_error(exc))

    def refresh_connectors(self) -> None:
        if not self.snapshot().capabilities.get("connectors", False):
            self.set_connector_health("unavailable")
            return
        with self._lock:
            if self._connector_inflight:
                return
            self._connector_inflight = True
        thread = threading.Thread(target=self._fetch_connectors, daemon=True, name="floating-connectors")
        thread.start()

    def _run_command(self, prompt: str) -> None:
        try:
            if self.orchestrator is not None:
                response = self.orchestrator.chat(prompt)
            else:
                response = self._post_chat(prompt)
            text = self._response_text(response)
            self.update(input="idle", assistant="listening", task="completed", message=text or "Command completed.", latest_response=text or "Command completed.", error=None)
        except Exception as exc:  # noqa: BLE001 - boundary converts errors to user state
            logger.warning("Floating command failed: %s", exc)
            self.update(input="error", assistant="error", task="failed", message="Command failed.", error=self._safe_error(exc))

    def _fetch_connectors(self) -> None:
        self.update(connectors="loading")
        try:
            response = self._request("GET", "/api/connector/status", timeout=3.0)
            if getattr(response, "status_code", 0) != 200:
                raise RuntimeError(f"Connector status returned HTTP {getattr(response, 'status_code', 'unknown')}")
            payload = response.json()
            connectors = payload.get("connectors", []) if isinstance(payload, dict) else []
            self.set_connector_health("ready", connectors)
        except Exception as exc:  # noqa: BLE001 - connector health is non-blocking
            logger.debug("Floating connector refresh failed: %s", exc)
            self.set_connector_health("stale", [])
        finally:
            with self._lock:
                self._connector_inflight = False

    def _post_chat(self, prompt: str) -> Any:
        response = self._request("POST", "/api/chat", json={"message": prompt}, timeout=self._http_timeout)
        if getattr(response, "raise_for_status", None):
            response.raise_for_status()
        return response.json()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        session = self._session
        if session is None:
            import requests

            session = requests
        port = os.environ.get("BR_SERVER_PORT") or os.environ.get("PORT") or "8000"
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.update(self._auth_headers())
        return session.request(method, f"http://127.0.0.1:{port}{path}", headers=headers, **kwargs)

    def _auth_headers(self) -> dict[str, str]:
        key = os.environ.get("SERVER_API_KEY") or os.environ.get("JARVIS_SERVER_API_KEY")
        if not key:
            config_root = self._config_root
            if config_root is None:
                try:
                    from brjarvis.core.paths import paths

                    config_root = paths.CONFIG_ROOT
                except Exception:
                    config_root = Path(__file__).resolve().parents[3] / "config"
            api_file = Path(config_root) / "api_keys.json"
            try:
                if api_file.exists():
                    payload = json.loads(api_file.read_text(encoding="utf-8"))
                    key = payload.get("server_api_key")
            except Exception:
                logger.debug("Unable to read floating-widget API key file", exc_info=True)
        if not key:
            return {}
        token = str(key).strip()
        return {"X-API-Key": token, "Authorization": f"Bearer {token}"}

    @staticmethod
    def _response_text(response: Any) -> str:
        if isinstance(response, str):
            return response.strip()
        if isinstance(response, Mapping):
            for key in ("response", "message", "text", "content"):
                if response.get(key):
                    return str(response[key]).strip()
        return str(response).strip() if response else ""

    @staticmethod
    def _safe_error(exc: BaseException) -> str:
        message = str(exc).strip() or exc.__class__.__name__
        lowered = message.lower()
        if any(token in lowered for token in ("httpconnectionpool", "connection refused", "max retries exceeded", "failed to establish a new connection", "connection aborted")):
            return "BR JARVIS backend is not reachable. Start the backend or retry."
        if "waittimeout" in lowered or "listening timed out" in lowered:
            return "Listening timed out. Click MIC to try again."
        if "timed out" in lowered or "timeout" in lowered:
            return "The request timed out. Check the backend and retry."
        if "handoff" in lowered:
            return "Workspace handoff expired. Click Open workspace to try again."
        return message[:240]
