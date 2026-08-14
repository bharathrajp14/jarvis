# tests/unit/test_mk37_upgrade.py — Comprehensive Unit & Integration Test Suite for BR JARVIS MK37
import json
import time
import unittest
from pathlib import Path

from agent.task_state import (
    TaskAction,
    TaskState,
    TaskStateManager,
    TaskStatus,
)
from agent.recovery_engine import (
    FailureCategory,
    RecoveryEngine,
    get_recovery_engine,
)
from tools.browser_agent_v2 import (
    BrowserActionType,
    BrowserObservation,
    InteractiveElement,
)
from skills.skill_engine import (
    SkillEngine,
    SkillSchema,
    SkillStep,
)
from actions.routine_engine import (
    RoutineDefinition,
    RoutineEngine,
    TriggerType,
)
from connectors.capabilities import (
    ApplicationCapability,
    CapabilityCategory,
    CapabilityRegistry,
    SensitivityLevel,
)
from mobile.protocol import (
    AccessibilityNode,
    DeviceState,
    MobileMessage,
    MobileMessageType,
)
from mobile.gateway import (
    DeviceGateway,
    PairedDevice,
)
from mobile.screen_understanding import (
    MobileScreenUnderstanding,
)
from mobile.mock_android import (
    MockAndroidDevice,
)
from mobile.device_controller import (
    AndroidDeviceController,
)
from agent.cross_device_planner import (
    CrossDevicePlanner,
    CrossDeviceStep,
    DeviceTarget,
)
from security.credentials import (
    CredentialVault,
)
from history.audit_engine import (
    AuditEngine,
)
from permissions import (
    ActionDecision,
    check_permission,
)


class TestMK37UpgradeSuite(unittest.TestCase):
    """Master Verification Test Suite for BR JARVIS MK37 Upgrade."""

    def setUp(self):
        import uuid
        self.temp_dir = Path(f"./workspace/test_temp_{uuid.uuid4().hex[:8]}")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                pass

    # ── 1. Autonomous Agent 2.0 Task State & Checkpointing ───────────────────
    def test_agent_task_state_machine(self):
        db_path = self.temp_dir / "test_tasks.db"
        if db_path.exists():
            db_path.unlink()
        mgr = TaskStateManager(db_path=db_path)

        # Create Task
        task = mgr.create_task("Research 30 Python Companies and report", total_steps=5, active_devices=["pc", "android"])
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertEqual(task.total_steps, 5)

        # Record Action & Checkpoint
        action = TaskAction(
            action_id="act_1",
            step_index=1,
            tool="web_search",
            parameters={"query": "python startups"},
            result="Found 30 companies",
            verified=True,
            duration=1.2
        )
        mgr.record_action(task.task_id, action)
        chk_id = mgr.create_checkpoint(task.task_id, step_index=1)
        self.assertTrue(chk_id.startswith("chk_"))

        # Approval Gate
        req = mgr.request_approval(task.task_id, "act_2", "Send report via WhatsApp", risk_level="high")
        self.assertEqual(req.status, "pending")
        task_paused = mgr.get_task(task.task_id)
        self.assertEqual(task_paused.status, TaskStatus.WAITING_APPROVAL)

        # Resolve Approval
        resolved = mgr.resolve_approval(task.task_id, req.request_id, approved=True)
        self.assertEqual(resolved.status, TaskStatus.RUNNING)

        # Complete
        completed = mgr.update_status(task.task_id, TaskStatus.COMPLETED)
        self.assertEqual(completed.status, TaskStatus.COMPLETED)

    # ── 2. Recovery Engine & Failure Taxonomy ────────────────────────────────
    def test_recovery_engine_taxonomy_and_loop_detection(self):
        engine = RecoveryEngine(max_consecutive_duplicates=3)

        # Test Captcha Detection
        analysis = engine.analyze_failure("browser", "recaptcha challenge detected on page")
        self.assertEqual(analysis.category, FailureCategory.CAPTCHA_REQUIRED)
        self.assertFalse(analysis.retry_allowed)

        # Test Locked State
        analysis = engine.analyze_failure("mobile_whatsapp", "device is locked with pin required")
        self.assertEqual(analysis.category, FailureCategory.AUTH_REQUIRED)

        # Test Missing UI Element
        analysis = engine.analyze_failure("browser_click", "element not found: button#submit")
        self.assertEqual(analysis.category, FailureCategory.ELEMENT_NOT_FOUND)
        self.assertTrue(analysis.retry_allowed)

        # Test Repetitive Stuck Loop Detection
        stuck1 = engine.check_loop_or_stuck("click_btn", '{"id": 1}')
        stuck2 = engine.check_loop_or_stuck("click_btn", '{"id": 1}')
        stuck3 = engine.check_loop_or_stuck("click_btn", '{"id": 1}')
        self.assertFalse(stuck1)
        self.assertFalse(stuck2)
        self.assertTrue(stuck3)  # Third consecutive call triggers loop alarm

        # Test Exponential Backoff
        self.assertEqual(engine.compute_backoff(1), 1.0)
        self.assertEqual(engine.compute_backoff(2), 2.0)
        self.assertEqual(engine.compute_backoff(3), 4.0)

    # ── 3. Strawberry-Class Browser Observation Models ───────────────────────
    def test_strawberry_browser_models(self):
        elem = InteractiveElement(
            element_id=1,
            tag="button",
            role="button",
            text="Apply Now",
            selector="button.apply-btn",
            is_visible=True
        )
        obs = BrowserObservation(
            url="https://careers.google.com",
            title="Careers",
            interactive_elements=[elem],
            dom_text_summary="Open Engineering Roles",
            captcha_detected=False
        )
        d = obs.to_dict()
        self.assertEqual(d["title"], "Careers")
        self.assertEqual(len(d["interactive_elements"]), 1)
        self.assertEqual(d["interactive_elements"][0]["text"], "Apply Now")

    # ── 4. Declarative Skills System ─────────────────────────────────────────
    def test_declarative_skills_system(self):
        skills_dir = self.temp_dir / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        engine = SkillEngine(storage_dir=skills_dir)

        skill = SkillSchema(
            name="qualify_lead",
            version="1.1.0",
            description="Qualify incoming sales lead and create summary",
            inputs=["lead_name", "company"],
            steps=[
                SkillStep(step_id="s1", tool="web_search", parameters={"query": "{company} revenue"}),
                SkillStep(step_id="s2", tool="doc_writer", parameters={"content": "Lead: {lead_name}"})
            ],
            verification=["doc_created"]
        )
        engine.save_skill(skill)
        loaded = engine.get_skill("qualify_lead")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.version, "1.1.0")

        # Test Execution Mock
        calls = []
        def dummy_caller(tool, params):
            calls.append((tool, params))
            return f"Executed {tool}"

        res = engine.execute_skill("qualify_lead", {"lead_name": "Alice", "company": "AcmeCorp"}, tool_caller=dummy_caller)
        self.assertTrue(res["success"])
        self.assertEqual(calls[0][1]["query"], "AcmeCorp revenue")
        self.assertEqual(calls[1][1]["content"], "Lead: Alice")

    # ── 5. Persistent Routines Engine ────────────────────────────────────────
    def test_persistent_routines_engine(self):
        r_dir = self.temp_dir / "routines"
        r_dir.mkdir(parents=True, exist_ok=True)
        engine = RoutineEngine(db_path=r_dir / "test_routines.db")

        r = engine.create_routine(
            name="Weekly GitHub Digest",
            goal="Summarize weekly repo PRs and issues",
            trigger_type=TriggerType.SCHEDULE,
            trigger_config={"interval": "every 7d"},
            target_device="pc"
        )
        self.assertTrue(r.enabled)
        loaded_list = engine.list_routines()
        self.assertEqual(len(loaded_list), 1)
        self.assertEqual(loaded_list[0].name, "Weekly GitHub Digest")

    # ── 6. Universal Capability Registry ─────────────────────────────────────
    def test_capability_registry(self):
        reg = CapabilityRegistry()
        caps = reg.list_capabilities(category=CapabilityCategory.COMMUNICATION)
        names = [c.name for c in caps]
        self.assertIn("gmail", names)
        self.assertIn("whatsapp", names)

        # Action lookup
        found = reg.find_capability_for_action("send_email")
        self.assertTrue(any(f.name == "gmail" for f in found))

    # ── 7. Mobile Protocol & Device Gateway ──────────────────────────────────
    def test_mobile_device_gateway_and_pairing(self):
        g_dir = self.temp_dir / "devices"
        g_dir.mkdir(parents=True, exist_ok=True)
        gateway = DeviceGateway(db_path=g_dir / "test_devices.db")

        # 1. Generate Pairing Token
        token_info = gateway.generate_pairing_token("Bharath Pixel 8")
        pin = token_info["pin"]
        self.assertEqual(len(pin), 6)

        # 2. Complete Pairing
        paired = gateway.complete_pairing(
            pin=pin,
            device_id="android_bharath_p8",
            model_name="Google Pixel 8 Pro",
            public_key="ed25519_pk_test123"
        )
        self.assertIsNotNone(paired)
        self.assertEqual(paired.trust_state, "trusted")

        # 3. Auth Token Verification
        valid = gateway.verify_auth_token("android_bharath_p8", paired.auth_token)
        self.assertTrue(valid)
        invalid = gateway.verify_auth_token("android_bharath_p8", "fake_token")
        self.assertFalse(invalid)

    # ── 8. Mobile Screen Understanding & Mock Android Device ─────────────────
    def test_mobile_screen_understanding_and_lock_rules(self):
        mock_phone = MockAndroidDevice()
        parser = MobileScreenUnderstanding()

        # WhatsApp screen inspection
        mock_phone.execute_action({"action": "open_app", "app_name": "whatsapp"})
        tree = mock_phone.get_accessibility_tree()

        match_rahul = parser.find_element(tree, "Rahul")
        self.assertIsNotNone(match_rahul)
        self.assertEqual(match_rahul.text, "Rahul")

        match_send = parser.find_element(tree, "Send")
        self.assertIsNotNone(match_send)

        # Test Locked State Behavior
        mock_phone.set_lock_state(True)
        locked_state = mock_phone.get_state()
        self.assertTrue(locked_state.is_locked)
        self.assertTrue(locked_state.requires_biometric_or_pin)

        locked_tree = mock_phone.get_accessibility_tree()
        summary = parser.summarize_screen(locked_tree)
        self.assertIn("Device Locked", summary)

    # ── 9. Cross-Device Task Decomposition ───────────────────────────────────
    def test_cross_device_planner(self):
        planner = CrossDevicePlanner()

        # Scenario: PC file search + Android WhatsApp send
        goal = "Find my resume on my PC and send it to Rahul on WhatsApp"
        steps = planner.plan_cross_device_task(goal)

        self.assertGreaterEqual(len(steps), 3)
        self.assertEqual(steps[0].device_target, DeviceTarget.PC)
        self.assertEqual(steps[1].device_target, DeviceTarget.MOBILE_ANDROID)
        self.assertEqual(steps[2].device_target, DeviceTarget.MOBILE_ANDROID)
        # Verify approval gate on message send
        self.assertTrue(steps[2].requires_approval)

    # ── 10. Security, Credentials Vault & Audit Logging ──────────────────────
    def test_security_credentials_and_audit(self):
        # Credential Vault
        vault_path = self.temp_dir / "test_vault.json"
        vault = CredentialVault(vault_path=vault_path)
        vault.store_credential("android_whatsapp_token", "secret_wa_token_987", {"user": "bharath"})
        val = vault.get_credential("android_whatsapp_token")
        self.assertEqual(val, "secret_wa_token_987")

        # Audit Logging
        audit_path = self.temp_dir / "test_audit.db"
        audit = AuditEngine(db_path=audit_path)
        ev = audit.log_event(
            task_id="task_123",
            device_id="android_bharath_p8",
            application="whatsapp",
            action="send_message",
            risk="high",
            approval="user",
            details={"contact": "Rahul", "file": "resume.pdf"},
            result="success"
        )
        self.assertEqual(ev.risk, "high")
        queried = audit.query_events(task_id="task_123")
        self.assertEqual(len(queried), 1)
        self.assertEqual(queried[0].action, "send_message")

        # Permissions
        self.assertEqual(ActionDecision.ALLOW.value, "allow")
        self.assertEqual(ActionDecision.CONFIRM.value, "confirm")


if __name__ == "__main__":
    unittest.main()
