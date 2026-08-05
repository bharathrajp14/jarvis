# tests/test_tool_suite_audit.py — Unit tests for JARVIS Tool Suite Audit & Hardening
from __future__ import annotations

import unittest
from tools.registry import TOOL_REGISTRY, TOOL_SCHEMAS, _import_plugins, execute_tool


class TestToolSuiteAudit(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _import_plugins()

    def test_all_plugins_imported(self):
        """Verify that all core and plugin tools are registered in TOOL_REGISTRY."""
        self.assertGreater(len(TOOL_REGISTRY), 25, "Expected at least 25 registered tools")
        self.assertGreater(len(TOOL_SCHEMAS), 25, "Expected at least 25 tool schemas")

    def test_newly_registered_tools_exist(self):
        """Verify that previously missing tools are registered."""
        expected_tools = [
            "semantic_file_search",
            "web_extractor",
            "system_health",
            "mcp_call_tool",
            "port_scan",
            "dns_enum",
            "headers_audit",
            "whois_lookup",
            "nmap_scan",
            "generate_report",
            "run_skill",
            "list_skills",
            "gmail_send",
            "gmail_reply",
            "ms365_control",
        ]
        for tool_name in expected_tools:
            self.assertIn(tool_name, TOOL_REGISTRY, f"Tool '{tool_name}' should be registered in TOOL_REGISTRY")

    def test_semantic_file_search_resilience(self):
        res = execute_tool("semantic_file_search", {"query": "voice"})
        self.assertIsInstance(res, str)
        self.assertIn("files", res.lower())

    def test_web_extractor_resilience(self):
        res = execute_tool("web_extractor", {"url": "https://example.com"})
        self.assertIsInstance(res, str)

    def test_system_health_resilience(self):
        res = execute_tool("system_health", {})
        self.assertIsInstance(res, str)
        self.assertIn("System Health", res)

    def test_window_manager_action_dict_resilience(self):
        from tools.window_manager import window_manager_action
        # Verify passing a dict as first argument doesn't raise AttributeError
        res = window_manager_action({"action": "list"})
        self.assertIsInstance(res, str)

    def test_gmail_send_alias_resilience(self):
        # Pass recipient instead of to
        res = execute_tool("gmail_send", {"recipient": "test@example.com", "subject": "Test", "body": "Hello"})
        self.assertIsInstance(res, str)
        # Should not throw KeyError

    def test_mcp_connector_resilience(self):
        from tools.mcp_connector import MCPConnector
        connector = MCPConnector("http://127.0.0.1:99999", timeout=0.1)
        res = connector.list_tools()
        self.assertEqual(res, [])
        err = connector.call_tool("test", {})
        self.assertIn("error", err)


if __name__ == "__main__":
    unittest.main()
