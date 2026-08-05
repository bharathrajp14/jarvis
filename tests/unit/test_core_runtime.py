# tests/test_core_runtime.py — Unit Tests for Priority 1 Core Runtime
from __future__ import annotations

import asyncio
import pytest
from core.config import JarvisConfig, get_config
from core.di import Container
from core.health import HealthMonitor, ComponentHealth
from core.lifecycle import LifecycleManager, SystemState
from core.logging import setup_logger
from core.process import ProcessSupervisor
from core.runtime import CoreRuntime, get_runtime


def test_pydantic_config_loading():
    config = get_config(force_reload=True)
    assert isinstance(config, JarvisConfig)
    assert config.assistant.name is not None
    assert config.models.default_backend is not None
    assert config.system.log_level in ("DEBUG", "INFO", "WARNING", "ERROR")


def test_dependency_injection_container():
    container = Container()

    class DummyService:
        def __init__(self):
            self.value = 42

    dummy = DummyService()
    container.register_instance(DummyService, dummy)

    resolved = container.resolve(DummyService)
    assert resolved is dummy
    assert resolved.value == 42


@pytest.mark.asyncio
async def test_lifecycle_manager():
    lifecycle = LifecycleManager()
    started = False
    stopped = False

    async def on_start():
        nonlocal started
        started = True

    async def on_stop():
        nonlocal stopped
        stopped = True

    lifecycle.add_startup_hook(on_start)
    lifecycle.add_shutdown_hook(on_stop)

    assert lifecycle.state == SystemState.UNINITIALIZED
    await lifecycle.startup()
    assert lifecycle.state == SystemState.RUNNING
    assert started is True

    await lifecycle.shutdown()
    assert lifecycle.state == SystemState.SHUTDOWN
    assert stopped is True


@pytest.mark.asyncio
async def test_process_supervisor():
    supervisor = ProcessSupervisor()
    executed = False

    async def sample_task():
        nonlocal executed
        await asyncio.sleep(0.01)
        executed = True
        return "done"

    task = supervisor.spawn("task-1", "sample_task", sample_task)
    res = await task
    assert res == "done"
    assert executed is True

    statuses = supervisor.list_tasks()
    assert "task-1" in statuses
    assert statuses["task-1"].status == "completed"


def test_health_monitor():
    monitor = HealthMonitor()
    monitor.register_check(
        "test_component",
        lambda: ComponentHealth(name="test_component", status="HEALTHY", message="Operational")
    )
    report = monitor.generate_report()
    assert report.overall_status in ("HEALTHY", "DEGRADED", "UNHEALTHY")
    assert "test_component" in report.components
    assert report.components["test_component"].status == "HEALTHY"


def test_core_runtime_singleton():
    runtime1 = get_runtime()
    runtime2 = get_runtime()
    assert runtime1 is runtime2
    assert isinstance(runtime1, CoreRuntime)
