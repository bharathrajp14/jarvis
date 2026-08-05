# tests/test_event_bus.py — Unit Tests for Priority 2 Asynchronous Event Bus
from __future__ import annotations

import asyncio
import pytest
from events.bus import EventBus, get_event_bus
from events.handlers import subscribe
from events.store import EventStore
from events.types import BaseEvent, SystemEvent, TaskEvent, ToolExecutionEvent


@pytest.mark.asyncio
async def test_event_bus_pub_sub():
    bus = EventBus(store=EventStore(persist_to_disk=False))
    received_events = []

    async def on_system_event(event: BaseEvent):
        received_events.append(event)

    bus.subscribe("system.*", on_system_event)

    evt1 = SystemEvent(topic="system.startup", state="RUNNING")
    evt2 = TaskEvent(topic="task.created", task_id="123", goal="Test task")

    await bus.publish_async(evt1)
    await bus.publish_async(evt2)

    assert len(received_events) == 1
    assert received_events[0].topic == "system.startup"


@pytest.mark.asyncio
async def test_event_store_query():
    store = EventStore(persist_to_disk=False)
    evt = ToolExecutionEvent(
        topic="tool.exec.start",
        tool_name="web_search",
        correlation_id="test-cid-999"
    )
    store.append(evt)

    results = store.query(correlation_id="test-cid-999")
    assert len(results) == 1
    assert results[0].payload is not None


@pytest.mark.asyncio
async def test_dead_letter_queue():
    bus = EventBus(store=EventStore(persist_to_disk=False))

    def failing_handler(event: BaseEvent):
        raise ValueError("Simulated handler crash")

    bus.subscribe("error.topic", failing_handler)
    evt = BaseEvent(topic="error.topic")

    await bus.publish_async(evt)

    dlq = bus.get_dlq()
    assert len(dlq) == 1
    assert dlq[0]["error"] == "Simulated handler crash"
