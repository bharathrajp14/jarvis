# tests/unit/test_desktop_actions.py
import pytest
from actions.desktop import _execute_generated_code, _safe_ast_execute


def test_safe_ast_execute_simple_assignment_and_call():
    code = """
def run_desktop_task():
    x = 10
    y = 20
    print(x + y)
"""
    logs = []
    scope = {"print": lambda val: logs.append(val)}
    _safe_ast_execute(code, scope)
    assert "run_desktop_task" in scope
    scope["run_desktop_task"]()
    assert logs == [30]


def test_execute_generated_code_success():
    code = """
def run_desktop_task():
    a = [1, 2, 3]
    b = len(a)
"""
    res = _execute_generated_code(code)
    assert "Task completed successfully." in res or "Script executed." in res or "Task executed successfully." in res


def test_execute_generated_code_unsafe_attribute_blocked():
    code = "x = (1).__class__"
    res = _execute_generated_code(code)
    assert "Security Block" in res or "Execution error" in res
