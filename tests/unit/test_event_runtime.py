from __future__ import annotations

import json

import pytest

from brjarvis.events.bus import EventBus
from brjarvis.events.store import EventStore
from brjarvis.events.types import BaseEvent


@pytest.mark.unit
def test_event_store_bounds_memory_and_persists_jsonl(tmp_path):
    event_path = tmp_path / "events.jsonl"
    store = EventStore(
        event_path=event_path,
        max_events=3,
        max_pending_writes=10,
        max_file_bytes=1024 * 1024,
    )
    try:
        for index in range(5):
            store.append(BaseEvent(topic=f"test.{index}", payload={"index": index}))
        store.flush()

        retained = store.query(limit=10)
        assert [event.topic for event in retained] == ["test.2", "test.3", "test.4"]
        persisted = [json.loads(line) for line in event_path.read_text(encoding="utf-8").splitlines()]
        assert [record["topic"] for record in persisted] == [
            "test.0",
            "test.1",
            "test.2",
            "test.3",
            "test.4",
        ]
        assert store.dropped_writes == 0
    finally:
        store.close()


@pytest.mark.unit
def test_event_store_rotates_large_jsonl_files(tmp_path):
    event_path = tmp_path / "events.jsonl"
    store = EventStore(
        event_path=event_path,
        max_events=10,
        max_file_bytes=1024,
        backup_count=2,
    )
    try:
        for index in range(8):
            store.append(BaseEvent(topic="test.rotate", payload={"index": index, "data": "x" * 400}))
        store.flush()

        assert event_path.exists()
        assert event_path.with_name("events.jsonl.1").exists()
    finally:
        store.close()


@pytest.mark.unit
def test_sync_publish_delivers_async_handler_without_running_loop():
    store = EventStore(persist_to_disk=False)
    bus = EventBus(store=store)
    received: list[str] = []

    async def async_handler(event: BaseEvent) -> None:
        received.append(event.topic)

    bus.subscribe("test.*", async_handler)
    bus.publish(BaseEvent(topic="test.delivered"))

    assert received == ["test.delivered"]
