# tests/test_router_scratchpad_queue.py
import pytest  # type: ignore[import-not-found]
import time
from router.core import get_router, AgentRouter, AgentProfile, ROUTING_RULES
from agent.scratchpad import get_scratchpad, ScratchpadManager
from agent.task_queue import TaskQueue, TaskPriority, TaskStatus


def test_router_singleton_and_rules():
    router = get_router()
    assert isinstance(router, AgentRouter)
    assert router.default in AgentProfile
    
    # Test keyword routing
    profile = router.route(["code"])
    assert profile in [AgentProfile.GEMINI, AgentProfile.CLAUDE, AgentProfile.GPT, AgentProfile.DEEPSEEK]


def test_scratchpad_operations():
    sp = get_scratchpad()
    assert isinstance(sp, ScratchpadManager)
    
    note_res = sp.add_note("Unit test scratch note")
    assert "Added scratch note" in note_res
    assert "Unit test scratch note" in sp.get_notes()[-1]
    
    file_res = sp.write_file("test_scratch.txt", "Hello Scratchpad")
    assert "Scratchpad file created" in file_res
    
    read_res = sp.read_file("test_scratch.txt")
    assert read_res == "Hello Scratchpad"
    
    eval_res = sp.eval_script("print('Hello from Scratch')", language="python")
    assert eval_res["success"] is True
    assert "Hello from Scratch" in eval_res["stdout"]


def test_task_queue_execution():
    queue = TaskQueue(max_concurrent=2)
    queue.start()

    task_id = queue.submit("Test Task Queue", priority=TaskPriority.HIGH)
    assert task_id is not None
    
    status = queue.get_status(task_id)
    assert status is not None
    assert status["task_id"] == task_id
    assert status["goal"] == "Test Task Queue"
    
    queue.cancel(task_id)
    cancelled_status = queue.get_status(task_id)
    assert cancelled_status["status"] == "cancelled"
    queue.stop()
