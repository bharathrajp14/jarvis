# tests/unit/test_canonical_contracts.py — Unit Tests for BR JARVIS Canonical Contracts
"""
Unit tests validating typed Pydantic contracts across all architectural planes.
"""
import time
import pytest

from brjarvis.contracts import (
    AgentRole,
    AgentRequest,
    AgentResponse,
    AgentDefinition,
    TaskStatus,
    TaskCriterion,
    TaskAction,
    ApprovalRequest,
    Task,
    TaskState,
    SessionState,
    SessionTurn,
    SessionCheckpoint,
    Session,
    Handoff,
    WorkflowStatus,
    WorkflowCheckpoint,
    WorkflowState,
    AgentEvent,
    EventEnvelope,
    ToolCategory,
    RiskLevel,
    ToolRequest,
    ToolResult,
    Capability,
    CapabilityLease,
    ModelCapability,
    ModelRequest,
    ModelResponse,
    ModelHealth,
    ModelSelection,
    ActionDecision,
    IdentityScope,
    PermissionContext,
    SecurityDecision,
    SecretReference,
    MemoryRecord,
    MemoryQuery,
    MemoryFeedbackRecord,
    EffectReceipt,
    VerificationStatus,
    VerificationResult,
)


@pytest.mark.unit
def test_agent_contracts():
    req = AgentRequest(query="Refactor module X", session_id="sess-01", role=AgentRole.CODING)
    assert req.query == "Refactor module X"
    assert req.role == AgentRole.CODING
    assert req.request_id.startswith("req-")

    resp = AgentResponse(request_id=req.request_id, session_id=req.session_id, text="Refactored successfully")
    assert resp.text == "Refactored successfully"
    assert resp.status == "completed"

    defn = AgentDefinition(agent_id="coding-agent", role=AgentRole.CODING, name="Coding Agent")
    assert defn.agent_id == "coding-agent"


@pytest.mark.unit
def test_task_contracts():
    crit = TaskCriterion(description="File exists")
    act = TaskAction(step_index=1, tool="file_write", parameters={"path": "test.txt"})
    task = Task(description="Create file", criteria=[crit], actions=[act])
    assert task.status == TaskStatus.PENDING
    assert len(task.criteria) == 1
    assert task.actions[0].tool == "file_write"

    state = TaskState(task_id=task.task_id, session_id="sess-01", goal="Create file", actions=[act])
    assert state.current_step_index == 0


@pytest.mark.unit
def test_session_and_handoff_contracts():
    sess = Session(session_id="sess-100", current_state=SessionState.ACTIVE)
    assert sess.current_state == SessionState.ACTIVE
    turn = SessionTurn(role="user", content="Hello Jarvis")
    sess.turns.append(turn)
    assert len(sess.turns) == 1

    hoff = Handoff(
        session_id=sess.session_id,
        source_agent="general",
        target_agent="coding",
        goal="Continue coding task",
        completed=["read files"],
        next_steps=["edit code"],
    )
    assert hoff.status == "OPEN"
    assert hoff.confidence == 1.0


@pytest.mark.unit
def test_workflow_contracts():
    ckpt = WorkflowCheckpoint(workflow_id="wf-01", node_id="node-1", state_payload={"step": 1})
    wf = WorkflowState(workflow_id="wf-01", status=WorkflowStatus.RUNNING, checkpoints=[ckpt])
    assert wf.status == WorkflowStatus.RUNNING
    assert len(wf.checkpoints) == 1


@pytest.mark.unit
def test_event_envelope():
    evt = AgentEvent(
        event_type="task.created",
        source="orchestrator",
        task_id="task-123",
        session_id="sess-456",
        payload={"goal": "Build system"},
    )
    assert evt.event_type == "task.created"
    assert evt.schema_version == "1.0"
    assert evt.trace_id.startswith("tr-")
    d = evt.to_dict()
    assert d["event_type"] == "task.created"


@pytest.mark.unit
def test_tool_and_capability_contracts():
    treq = ToolRequest(tool_name="shell.exec", parameters={"cmd": "dir"})
    assert treq.environment == "host"

    tres = ToolResult(tool_name="shell.exec", output="Directory listing", verified=True)
    assert tres.success is True

    cap = Capability(id="shell.exec", name="Shell Execute", category=ToolCategory.SHELL, risk_level=RiskLevel.HIGH)
    assert cap.risk_level == RiskLevel.HIGH

    lease = CapabilityLease(agent_id="agent-01", task_id="task-01", capability="shell.exec", max_calls=2)
    assert lease.is_valid() is True
    lease.calls_used = 2
    assert lease.is_valid() is False


@pytest.mark.unit
def test_model_contracts():
    mreq = ModelRequest(model_id="gemini-3.7-flash", messages=[{"role": "user", "content": "Hi"}])
    assert mreq.temperature == 0.2

    mresp = ModelResponse(request_id=mreq.request_id, text="Hello!", model="gemini-3.7-flash")
    assert mresp.has_tool_calls() is False

    sel = ModelSelection(model_id="gemini-3.7-flash", provider="google", score=0.95, reason="Best for task")
    assert sel.score == 0.95


@pytest.mark.unit
def test_security_contracts():
    ctx = PermissionContext(action="file_delete", capability="filesystem.write", risk_level="high")
    dec = SecurityDecision(decision=ActionDecision.REQUIRE_APPROVAL, reason="Destructive tool invocation")
    assert dec.is_allowed() is False
    assert dec.decision == ActionDecision.REQUIRE_APPROVAL


@pytest.mark.unit
def test_verification_and_receipts():
    rcpt = EffectReceipt(
        action_id="act-01",
        expected_effect="file test.txt created with > 0 bytes",
        observed_effect="file test.txt exists (size: 42 bytes)",
        verified=True,
        evidence="path=d:/test.txt, size=42",
        source="host_verifier",
    )
    assert rcpt.verified is True
    res = VerificationResult(verified=True, status=VerificationStatus.SUCCESS_VERIFIED, receipt=rcpt)
    assert res.status == VerificationStatus.SUCCESS_VERIFIED
