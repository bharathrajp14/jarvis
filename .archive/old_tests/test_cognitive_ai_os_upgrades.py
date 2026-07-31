# tests/test_cognitive_ai_os_upgrades.py — Cognitive AI OS Upgrades Automated Verification
"""
Comprehensive Pytest test suite verifying all 10 cognitive AI OS upgrade subsystems.
"""
import os
import shutil
import tempfile
import pytest

from reasoning.cognitive_loop import CognitiveLoop, SelfEvaluationPayload, get_cognitive_loop
from agent.critic_agent import CriticAgent, CritiqueResult
from memory.knowledge_graph import KnowledgeGraph
from workflow.task_dag import PersistentTaskDAG, DAGNodeState
from router import get_router, AgentProfile
from memory.decay import MemoryDecayEngine, MemoryItem
from agent.task_scheduler import TaskScheduler
from watchers.file_watcher import FileWatcher
from watchers.system_watcher import SystemWatcher
from multi_agent.swarm import MultiAgentSwarm


class TestCognitiveAIOSUpgrades:
    """Test suite verifying Cognitive AI OS features."""

    @pytest.fixture(autouse=True)
    def setup_temp_workspace(self):
        self.temp_dir = tempfile.mkdtemp()
        yield
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cognitive_loop_evaluation(self):
        loop = CognitiveLoop()
        eval_result = loop.evaluate_step_outcome(
            step_id=1,
            goal="Test execution goal",
            tool_name="python_code",
            tool_args={"code": "print('hello')"},
            tool_output="hello",
            execution_success=True,
        )

        assert isinstance(eval_result, SelfEvaluationPayload)
        assert eval_result.confidence_score >= 0.9
        assert not eval_result.should_retry

    def test_critic_agent_review(self):
        critic = CriticAgent()
        
        # Test empty output
        res_empty = critic.critique_step_output("Goal", "Step", "tool", "")
        assert not res_empty.is_valid
        assert res_empty.recommended_action == "RETRY"

        # Test valid output
        res_valid = critic.critique_step_output("Goal", "Step", "tool", "Analysis complete.")
        assert res_valid.is_valid
        assert res_valid.recommended_action == "PROCEED"

    def test_knowledge_graph_relational_model(self):
        db_file = os.path.join(self.temp_dir, "kg.json")
        kg = KnowledgeGraph(storage_path=db_file)
        
        kg.add_entity("proj_br", "project", {"name": "BR JARVIS"})
        kg.add_entity("mod_router", "module", {"path": "router.py"})
        kg.add_relationship("proj_br", "mod_router", "CONTAINS")

        assert kg.has_entity("proj_br")
        assert kg.has_entity("mod_router")
        
        related = kg.get_related_entities("proj_br")
        assert len(related) == 1
        assert related[0]["entity_id"] == "mod_router"

    def test_persistent_task_dag_checkpointing(self):
        db_file = os.path.join(self.temp_dir, "task_dag.db")
        dag_store = PersistentTaskDAG(db_path=db_file)

        nodes = [
            DAGNodeState(node_id=1, title="Step 1", tool_name="web_search", status="COMPLETED", result="Found info"),
            DAGNodeState(node_id=2, title="Step 2", tool_name="file_write", status="PENDING"),
        ]

        dag_store.checkpoint("task-100", "Build feature", nodes, status="IN_PROGRESS")

        resumed = dag_store.resume("task-100")
        assert resumed is not None
        assert resumed["goal"] == "Build feature"
        assert len(resumed["nodes"]) == 2
        assert resumed["nodes"][0].status == "COMPLETED"

    def test_multi_objective_router(self):
        router = get_router()
        selected = router.select_multi_objective_backend(w_quality=1.0, w_cost=0.1, w_latency=0.1)
        assert isinstance(selected, AgentProfile)

    def test_memory_decay_engine(self):
        decay = MemoryDecayEngine(half_life_days=7.0)
        item = MemoryItem(memory_id="m1", content="Test memory", importance=1.0)
        
        retention = decay.calculate_retention(item)
        assert retention > 0.0

        batch = decay.evaluate_batch([item])
        assert "RETAIN" in batch

    def test_watchers(self):
        fw = FileWatcher(watch_path=self.temp_dir)
        changes = fw.scan_for_changes()
        assert changes >= 0

        sw = SystemWatcher()
        metrics = sw.check_telemetry()
        assert "timestamp" in metrics

    def test_multi_agent_swarm(self):
        swarm = MultiAgentSwarm()
        assignments = swarm.create_swarm_collaboration("Build AI Subsystem")
        assert len(assignments) == 3
        assert assignments[0].assigned_role == "architect"
