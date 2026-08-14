# tests/test_gmail_auth.py — Verification suite for Gmail Authentication & Login Manager
"""
Automated unit & integration test suite verifying Gmail authentication, credential storage,
browser sign-in trigger, logout, and tool execution via registry.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Ensure root project path is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
logger = logging.getLogger("TestGmailAuth")

from actions.gmail_auth import get_gmail_auth_manager, GmailAuthManager
from tools.registry import execute_tool, TOOL_REGISTRY, _import_plugins



class TestGmailAuth(unittest.TestCase):

    def setUp(self):
        _import_plugins()
        self.mgr = get_gmail_auth_manager()

    def tearDown(self):
        self.mgr.logout()

    def test_01_gmail_auth_credentials_flow(self):
        """Test configuring and storing Gmail credentials."""
        res = self.mgr.configure_credentials("user.test@gmail.com", "abcd efgh ijkl mnop")
        self.assertIn("configured successfully", res)

        status = self.mgr.get_status()
        self.assertTrue(status["logged_in"])
        self.assertEqual(status["email"], "user.test@gmail.com")
        self.assertEqual(status["auth_method"], "app_password")
        self.assertEqual(os.environ.get("GMAIL_ADDRESS"), "user.test@gmail.com")
        logger.info(f"\n[Test] Gmail credentials configuration status: {status}")

    def test_02_gmail_auth_logout(self):
        """Test logging out and clearing saved credentials."""
        self.mgr.configure_credentials("user.test@gmail.com", "abcd efgh ijkl mnop")
        logout_res = self.mgr.logout()
        self.assertIn("signed out", logout_res)

        status = self.mgr.get_status()
        self.assertFalse(status["logged_in"])
        self.assertIsNone(os.environ.get("GMAIL_ADDRESS"))
        logger.info(f"[Test] Gmail logout output: {logout_res}")

    def test_03_gmail_tools_registry(self):
        """Test Gmail authentication tools via registry."""
        from tools.registry import _import_plugins
        _import_plugins(full=True)
        tools_to_test = ["gmail_login", "get_gmail_auth_status", "gmail_logout"]

        for t_name in tools_to_test:
            self.assertIn(t_name, TOOL_REGISTRY)

        # Test initial status tool call
        out1 = execute_tool("get_gmail_auth_status", {})
        self.assertIn("Gmail Status:", out1)
        logger.info(f"[Test] Tool 'get_gmail_auth_status' output:\n{out1}")

        # Test credentials login tool call
        out2 = execute_tool("gmail_login", {
            "mode": "credentials",
            "email": "demo.jarvis@gmail.com",
            "app_password": "xxxx yyyy zzzz wwww"
        })
        self.assertIn("configured successfully", out2)

        out3 = execute_tool("get_gmail_auth_status", {})
        self.assertIn("LOGGED IN", out3)
        self.assertIn("demo.jarvis@gmail.com", out3)
        logger.info(f"[Test] Tool status after login:\n{out3}")

        # Test logout tool call
        out4 = execute_tool("gmail_logout", {})
        self.assertIn("signed out", out4)


if __name__ == "__main__":
    unittest.main()
