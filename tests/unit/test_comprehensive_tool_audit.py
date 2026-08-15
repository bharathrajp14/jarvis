# tests/unit/test_comprehensive_tool_audit.py — End-to-End Capability & Registry Verification Suite
from __future__ import annotations

import json
import unittest
from tools.registry import TOOL_REGISTRY, TOOL_SCHEMAS, _import_plugins, execute_tool, get_pruned_tool_prompt_block


class TestComprehensiveToolAudit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import os
        from permissions import PERMISSIONS, PermissionMode
        cls._orig_perm = os.environ.get("JARVIS_PERMISSION_MODE")
        cls._orig_mode = PERMISSIONS.mode
        os.environ["JARVIS_PERMISSION_MODE"] = "allow_all"
        PERMISSIONS.mode = PermissionMode.ALLOW_ALL
        _import_plugins(full=True)

    @classmethod
    def tearDownClass(cls):
        import os
        from permissions import PERMISSIONS
        PERMISSIONS.mode = cls._orig_mode
        if cls._orig_perm is not None:
            os.environ["JARVIS_PERMISSION_MODE"] = cls._orig_perm
        else:
            os.environ.pop("JARVIS_PERMISSION_MODE", None)

    def test_total_registered_tools_count(self):
        """Verify that all core and extended tools are registered (>180 tools)."""
        self.assertGreaterEqual(len(TOOL_REGISTRY), 180, f"Expected at least 180 registered tools, found {len(TOOL_REGISTRY)}")
        self.assertGreaterEqual(len(TOOL_SCHEMAS), 180, f"Expected at least 180 schemas, found {len(TOOL_SCHEMAS)}")

    def test_repaired_missing_tools_registered(self):
        """Verify that the 22 tools from the 8 previously unregistered modules are now present."""
        repaired_tools = [
            "add_background_monitor",
            "remove_background_monitor",
            "list_monitored_topics",
            "check_monitored_topics",
            "connector_status",
            "connector_call",
            "connector_search",
            "connector_add_mcp",
            "connector_list_tools",
            "import_contacts",
            "manage_contacts",
            "resolve_contact",
            "import_file_to_knowledge",
            "process_universal_file",
            "remember_that",
            "schedule_reminder",
            "manage_reminders",
            "scratchpad_write",
            "scratchpad_read",
            "scratchpad_eval",
            "scratchpad_list",
            "scratchpad_clear",
        ]
        for t in repaired_tools:
            self.assertIn(t, TOOL_REGISTRY, f"Repaired tool '{t}' must be in TOOL_REGISTRY")
            # Verify schema exists
            schema_names = [s.get("name") for s in TOOL_SCHEMAS]
            self.assertIn(t, schema_names, f"Repaired tool '{t}' must have a schema in TOOL_SCHEMAS")

    def test_connector_status_execution(self):
        """Verify connector_status executes and returns hub report."""
        res = execute_tool("connector_status", {})
        self.assertIsInstance(res, str)
        self.assertTrue("Connector Hub" in res or "connectors" in res.lower() or "Wikipedia" in res)

    def test_scratchpad_tools_execution(self):
        """Verify scratchpad tools write, read, and eval."""
        write_res = execute_tool("scratchpad_write", {"name": "test_audit.py", "content": "print('AUDIT_OK')"})
        self.assertTrue("test_audit.py" in write_res or "Scratchpad" in write_res)

        read_res = execute_tool("scratchpad_read", {"name": "test_audit.py"})
        self.assertIn("AUDIT_OK", read_res)

        eval_res = execute_tool("scratchpad_eval", {"script": "test_audit.py"})
        self.assertIn("AUDIT_OK", eval_res)

        clear_res = execute_tool("scratchpad_clear", {})
        self.assertIn("cleared", clear_res.lower())

    def test_contact_tools_execution(self):
        """Verify contact tools execute without crashing."""
        res = execute_tool("manage_contacts", {"action": "list"})
        self.assertIsInstance(res, str)

        resolve_res = execute_tool("resolve_contact", {"name": "NonExistentContact"})
        self.assertIn("not found", resolve_res.lower())

    def test_app_connectors_no_fake_mock_success(self):
        """Verify app connectors call ConnectorHub and do not emit fake hardcoded mock JSON."""
        # Unconfigured GitHub list_prs should return unconfigured hint or empty results, not hardcoded PR #36/#37
        res = execute_tool("github_list_prs", {"repo": "bharthraj1412/BrJarvis"})
        self.assertIsInstance(res, str)
        # Should not contain the old hardcoded sample PR titles
        self.assertNotIn("ui: Glassmorphic dark assistant redesign", res)

    def test_intent_pruned_prompt_block_domains(self):
        """Verify pruned tool prompt block correctly resolves new domains."""
        # Contact query
        block = get_pruned_tool_prompt_block("Please import my contacts from vcf file")
        self.assertIn("import_contacts", block)

        # Connector query
        block_conn = get_pruned_tool_prompt_block("Check connector status for notion and slack")
        self.assertIn("connector_status", block_conn)

        # Scratchpad query
        block_sp = get_pruned_tool_prompt_block("Write a scratchpad code snippet")
        self.assertIn("scratchpad_write", block_sp)


if __name__ == "__main__":
    unittest.main()
