from brjarvis.gateway.routing import AIGatewayRouter, GatewayResponse
from brjarvis.router.core import AgentRouter, PrivacyMode


class FakeBackend:
    def __init__(self, text: str, fail: bool = False):
        self.text = text
        self.fail = fail

    def complete(self, messages, system="", tools=None):
        if self.fail:
            raise RuntimeError("backend unavailable")
        return self.text


def make_router(data=None):
    data = data or {
        "cooldown_seconds": 0,
        "backends": [
            {"id": "local", "provider": "ollama", "model": "llama", "priority": 10, "latency_ms": 50, "capabilities": ["chat"]},
            {"id": "cloud", "provider": "proxy", "model": "gpt", "priority": 20, "latency_ms": 200, "capabilities": ["chat", "code"]},
        ],
        "routes": {
            "default": {"strategy": "priority", "backends": ["local", "cloud"]},
            "code": {"strategy": "latency", "backends": ["local", "cloud"], "required_capabilities": ["code"]},
            "cycle": {"strategy": "round_robin", "backends": ["local", "cloud"]},
        },
    }
    return AIGatewayRouter.from_mapping(data)


def test_priority_route_is_deterministic():
    router = make_router()
    decision = router.route()
    assert decision.selected_backend == "local"
    assert decision.candidates == ("local", "cloud")


def test_capabilities_filter_out_incompatible_backend():
    router = make_router()
    decision = router.route("code", capability="code")
    assert decision.selected_backend == "cloud"
    assert decision.candidates == ("cloud",)


def test_round_robin_cycles_candidates():
    router = make_router()
    assert router.route("cycle").selected_backend == "local"
    assert router.route("cycle").selected_backend == "cloud"
    assert router.route("cycle").selected_backend == "local"


def test_agent_router_can_delegate_to_gateway_policy():
    class StubGateway:
        def complete(self, **kwargs):
            assert kwargs["policy"] == "coding"
            assert kwargs["capability"] == "code"
            return GatewayResponse("gateway answer", "cloud", "gpt", ("cloud",))

        def status(self):
            return []

    router = AgentRouter(backends={}, privacy_mode=PrivacyMode.CLOUD_OPTIONAL, gateway_router=StubGateway())
    assert router.run("code", [{"role": "user", "content": "review code"}], "", routing_policy="coding", capability="code") == "gateway answer"
    assert router.fallback_history[-1]["policy"] == "coding"


def test_completion_falls_back_and_records_attempts():
    router = make_router()
    router.register("local", FakeBackend("ignored", fail=True))
    router.register("cloud", FakeBackend("cloud answer"))
    response = router.complete([{"role": "user", "content": "hello"}])
    assert response.text == "cloud answer"
    assert response.backend_id == "cloud"
    assert response.attempts == ("local", "cloud")
    assert router.status()[0]["failures"] == 1
