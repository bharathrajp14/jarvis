# tests/unit/test_agent_session.py — Unit Tests for Canonical AgentSession Model
from __future__ import annotations

from brjarvis.agent.session import (
    AgentSession,
    get_or_create_session,
    list_active_sessions,
)


class TestAgentSession:
    """Test suite for AgentSession state model and lifecycle."""

    def test_session_initialization(self):
        sess = AgentSession(
            session_id="test-sess-1",
            current_mode="coder",
            active_model="claude",
            permission_mode="confirm_destructive",
        )
        assert sess.session_id == "test-sess-1"
        assert sess.current_mode == "coder"
        assert sess.active_model == "claude"
        assert sess.permission_mode == "confirm_destructive"
        assert len(sess.turns) == 0
        assert not sess.is_closed

    def test_add_turns(self):
        sess = AgentSession(session_id="test-sess-turns")
        u_turn = sess.add_user_turn("Refactor the websocket server")
        assert u_turn.role == "user"
        assert u_turn.content == "Refactor the websocket server"
        assert len(sess.turns) == 1

        a_turn = sess.add_assistant_turn(
            content="Refactored websocket server.",
            tool_calls=[{"tool": "file_write", "args": {"path": "server.py"}}],
            tool_results=[{"tool": "file_write", "result": "Written 100 bytes"}],
            latency_ms=150,
        )
        assert a_turn.role == "assistant"
        assert len(sess.turns) == 2
        assert len(a_turn.tool_calls) == 1
        assert a_turn.latency_ms == 150

    def test_tool_and_verification_tracking(self):
        sess = AgentSession(session_id="test-sess-tools")
        sess.record_tool_call(
            tool_name="file_write",
            args={"path": "test.txt", "content": "hello"},
            result="File written",
            duration_ms=45.0,
            verified=True,
            step_id="step-1",
        )
        assert len(sess.tool_history) == 1
        assert sess.tool_history[0]["tool_name"] == "file_write"
        assert sess.tool_history[0]["verified"] is True

        sess.record_verification(
            tool_name="file_write",
            target="test.txt",
            verified=True,
            evidence="File verified on disk (5 bytes)",
        )
        assert len(sess.verification_results) == 1
        assert sess.verification_results[0]["verified"] is True
        assert "5 bytes" in sess.verification_results[0]["evidence"]

    def test_plan_and_task_management(self):
        sess = AgentSession(session_id="test-sess-plan")
        sess.set_active_task("task-123", "Build API Service")
        assert sess.active_task_id == "task-123"
        assert sess.active_task_label == "Build API Service"

        plan = {
            "goal": "Build API Service",
            "steps": [
                {"step": 1, "description": "Create routes", "status": "pending"},
                {"step": 2, "description": "Add tests", "status": "pending"},
            ],
        }
        sess.set_plan(plan)
        sess.update_plan_step(1, status="completed", result="Routes created")
        assert sess.active_plan["steps"][0]["status"] == "completed"

        # Dynamic plan mutations
        new_step_idx = sess.add_plan_step("Run Integration Tests", tool="run_code")
        assert new_step_idx == 3
        assert len(sess.active_plan["steps"]) == 3

        sess.mark_step_blocked(2, reason="Missing database credentials")
        assert sess.active_plan["steps"][1]["status"] == "blocked"

        sess.retry_step(2)
        assert sess.active_plan["steps"][1]["status"] == "pending"

        removed = sess.remove_plan_step(3)
        assert removed is True
        assert len(sess.active_plan["steps"]) == 2

        sess.clear_active_task()
        assert sess.active_task_id is None
        assert len(sess.task_history) == 1

    def test_model_switching_and_permissions(self):
        sess = AgentSession(session_id="test-sess-sw")
        sess.switch_model("claude", strategy="adaptive")
        assert sess.active_model == "claude"
        assert sess.model_strategy == "adaptive"

        sess.set_permission_mode("allow_all")
        assert sess.permission_mode == "allow_all"

    def test_serialization(self):
        sess = AgentSession(session_id="test-sess-ser", current_mode="analyst")
        sess.add_user_turn("Analyze logs")
        sess.add_assistant_turn("Logs analyzed.")
        data = sess.to_dict()

        restored = AgentSession.from_dict(data)
        assert restored.session_id == "test-sess-ser"
        assert restored.current_mode == "analyst"
        assert len(restored.turns) == 2

    def test_session_registry(self):
        s1 = get_or_create_session("sess-reg-1", mode="coder")
        s2 = get_or_create_session("sess-reg-1")
        assert s1 is s2
        assert s1.current_mode == "coder"

        all_sess = list_active_sessions()
        assert any(s.session_id == "sess-reg-1" for s in all_sess)

    def test_session_checkpoint_and_resume(self):
        sess = AgentSession(session_id="test-sess-ckpt", current_mode="coder")
        sess.add_user_turn("Initial query")
        sess.add_assistant_turn("Initial response")
        sess.set_active_task("task-ckpt-1", "Checkpoint Task")

        # Create checkpoint
        ckpt_id = sess.checkpoint("turn_2_snapshot")
        assert ckpt_id.startswith("ckpt-")

        # Mutate session
        sess.add_user_turn("New query that broke things")
        sess.add_assistant_turn("Broken response")
        assert len(sess.turns) == 4

        # Resume from checkpoint
        resumed = sess.resume_from_checkpoint(ckpt_id)
        assert resumed is True
        assert len(sess.turns) == 2
        assert sess.active_task_id == "task-ckpt-1"

    def test_session_pause_and_cancel(self):
        sess = AgentSession(session_id="test-sess-pc", current_mode="general")
        sess.pause(reason="Waiting for user input")
        assert sess.current_state == "PAUSED"

        sess.resume_session()
        assert sess.current_state == "ACTIVE"

        sess.cancel(reason="User terminated")
        assert sess.current_state == "CANCELLED"
        assert sess.is_cancelled is True

    def test_session_compaction(self):
        sess = AgentSession(session_id="test-sess-compact")
        for i in range(10):
            sess.add_user_turn(f"Question {i}")
            sess.add_assistant_turn(f"Answer {i}")
        assert len(sess.turns) == 20

        sess.compact(summary="Discussed math and science problems from Q0 to Q9", retain_last=4)
        assert len(sess.turns) == 5  # 1 summary turn + 4 retained turns
        assert sess.turns[0].role == "system"
        assert "Session Compaction Summary" in sess.turns[0].content

    def test_session_handoff(self):
        sess = AgentSession(session_id="test-sess-hoff")
        sess.add_user_turn("Build frontend")
        sess.add_assistant_turn("Created components")

        hoff = sess.create_handoff(
            target_agent="jarvis-reviewer",
            goal="Review frontend UI components",
            next_steps=["Run linter", "Verify visual aesthetics"],
        )
        assert hoff["handoff_id"].startswith("hoff-")
        assert hoff["target_agent"] == "jarvis-reviewer"
        assert "Run linter" in hoff["next_steps"]

    def test_session_database_persistence(self):
        from brjarvis.agent.session import delete_session, reset_active_session

        sess_id = "test-sess-db-persist"
        sess = get_or_create_session(sess_id, mode="research")
        sess.add_user_turn("Research quantum computing algorithms")
        sess.add_assistant_turn("Quantum algorithms summary...")
        sess.save_to_store()

        # Clear in-memory cache to simulate process restart
        reset_active_session()

        # Re-fetch session from canonical DB
        recovered = get_or_create_session(sess_id)
        assert recovered.session_id == sess_id
        assert recovered.current_mode == "research"
        assert len(recovered.turns) == 2
        assert "quantum computing" in recovered.turns[0].content

        delete_session(sess_id)
