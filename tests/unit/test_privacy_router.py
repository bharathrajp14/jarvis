# tests/unit/test_privacy_router.py — Unit Tests for Model Router & Privacy Policy
from __future__ import annotations

import unittest
from router.core import AgentProfile, AgentRouter, PrivacyMode
from backends.base import BaseBackend


class DummyLocalBackend(BaseBackend):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    @property
    def name(self) -> str:
        return "DummyLocal"

    @property
    def model_name(self) -> str:
        return "dummy-local-v1"

    @property
    def is_local(self) -> bool:
        return True

    @property
    def available(self) -> bool:
        return True

    def complete(self, messages: list[dict], system: str = "", tools: list | None = None) -> str:
        if self.should_fail:
            raise RuntimeError("Local backend simulated error")
        return "Local response"

    def stream(self, messages: list[dict], system: str = ""):
        yield "Local response"


class DummyCloudBackend(BaseBackend):
    @property
    def name(self) -> str:
        return "DummyCloud"

    @property
    def model_name(self) -> str:
        return "dummy-cloud-v1"

    @property
    def is_local(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        return True

    def complete(self, messages: list[dict], system: str = "", tools: list | None = None) -> str:
        return "Cloud response"

    def stream(self, messages: list[dict], system: str = ""):
        yield "Cloud response"


class TestPrivacyRouter(unittest.TestCase):

    def test_local_only_mode_routes_to_local(self):
        backends = {
            AgentProfile.OLLAMA: DummyLocalBackend(),
            AgentProfile.GEMINI: DummyCloudBackend(),
        }
        router = AgentRouter(backends=backends, privacy_mode=PrivacyMode.LOCAL_ONLY)
        profile = router.route(["code"])
        self.assertEqual(profile, AgentProfile.OLLAMA)
        
        result = router.run(profile, [{"role": "user", "content": "hello"}], "")
        self.assertEqual(result, "Local response")

    def test_local_only_mode_blocks_cloud_fallback_when_local_fails(self):
        backends = {
            AgentProfile.OLLAMA: DummyLocalBackend(should_fail=True),
            AgentProfile.GEMINI: DummyCloudBackend(),
        }
        router = AgentRouter(backends=backends, privacy_mode=PrivacyMode.LOCAL_ONLY)
        result = router.run(AgentProfile.OLLAMA, [{"role": "user", "content": "private prompt"}], "")
        
        # Must NOT return Cloud response!
        self.assertNotIn("Cloud response", result)
        self.assertIn("LOCAL_ONLY", result)

    def test_cloud_mode_allows_cloud_execution(self):
        backends = {
            AgentProfile.GEMINI: DummyCloudBackend(),
        }
        router = AgentRouter(backends=backends, privacy_mode=PrivacyMode.CLOUD_OPTIONAL)
        result = router.run(AgentProfile.GEMINI, [{"role": "user", "content": "hello"}], "")
        self.assertEqual(result, "Cloud response")


if __name__ == "__main__":
    unittest.main()
