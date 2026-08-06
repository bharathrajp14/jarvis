"""Non-destructive startup smoke checks for JARVIS MK37.

This script validates core imports and lightweight runtime invariants without
calling external APIs or opening UI windows.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _check(name: str, fn):
    try:
        fn()
        if 'logger' in globals() or 'logger' in locals():
            logger.info(f"{ f"[PASS] {name}" }" if isinstance(f"[PASS] {name}", str) else f"[PASS] {name}")
        else:
            import logging
            logging.getLogger(__name__).info(f"{ f"[PASS] {name}" }" if isinstance(f"[PASS] {name}", str) else f"[PASS] {name}")
        return True
    except Exception as exc:
        if 'logger' in globals() or 'logger' in locals():
            logger.info(f"{ f"[FAIL] {name}: {exc}" }" if isinstance(f"[FAIL] {name}: {exc}", str) else f"[FAIL] {name}: {exc}")
        else:
            import logging
            logging.getLogger(__name__).info(f"{ f"[FAIL] {name}: {exc}" }" if isinstance(f"[FAIL] {name}: {exc}", str) else f"[FAIL] {name}: {exc}")
        return False


def main() -> int:
    root = _repo_root()
    sys.path.insert(0, str(root))

    results: list[bool] = []

    def check_permissions_module():
        from permissions import PERMISSIONS, PermissionMode

        assert PERMISSIONS.mode in (
            PermissionMode.ALLOW_ALL,
            PermissionMode.CONFIRM_DESTRUCTIVE,
            PermissionMode.CONFIRM_ALL,
            PermissionMode.DENY_ALL,
        )
        assert PERMISSIONS.check("web_search") in (True, False)

    def check_router_empty_backend_behavior():
        from router import AgentRouter, AgentProfile

        router = AgentRouter({})
        res = router.run(AgentProfile.GEMINI, [], "")
        assert "all backends failed" in res.lower() or "no backends available" in res.lower()

    def check_skills_registry():
        from skills import load_skills

        skills = load_skills()
        assert len(skills) >= 10

    def check_tools_registry():
        from tools.registry import TOOL_SCHEMAS, _import_plugins

        _import_plugins()
        assert len(TOOL_SCHEMAS) >= 30

    def check_scope_json_format():
        scope_path = root / "current_scope.json"
        assert scope_path.exists()
        payload = json.loads(scope_path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        assert isinstance(payload.get("permissions", {}), dict)

    def check_app_connectors_suite():
        from tools.app_connectors import gmail_list_unread, notion_search_pages, github_list_prs
        assert callable(gmail_list_unread)
        assert callable(notion_search_pages)
        assert callable(github_list_prs)

    def check_deepseek_backend_connector():
        from backends.deepseek import DeepSeekBackend
        ds = DeepSeekBackend(api_key="test_key_dummy")
        assert ds.model_name in ("deepseek-chat", "deepseek/deepseek-r1")

    def check_native_c_acceleration():
        from core.native_bridge import get_status, audio_energy
        st = get_status()
        assert "active" in st
        rms = audio_energy([0.1, 0.2, -0.1])
        assert rms >= 0.0

    def check_pwa_assets():
        manifest = root / "web" / "manifest.json"
        sw = root / "web" / "sw.js"
        assert manifest.exists(), "web/manifest.json missing"
        assert sw.exists(), "web/sw.js missing"

    def check_di_container():
        from core.di import Container
        c = Container()
        c.register_instance(str, "test_val")
        assert c.resolve(str) == "test_val"

    checks = [
        ("permissions module", check_permissions_module),
        ("router empty backend behavior", check_router_empty_backend_behavior),
        ("skills registry", check_skills_registry),
        ("tools registry", check_tools_registry),
        ("scope file format", check_scope_json_format),
        ("app connectors suite", check_app_connectors_suite),
        ("deepseek backend connector", check_deepseek_backend_connector),
        ("native C acceleration bridge", check_native_c_acceleration),
        ("pwa manifest & service worker", check_pwa_assets),
        ("di container & runtime", check_di_container),
    ]

    for name, fn in checks:
        results.append(_check(name, fn))

    passed = sum(1 for ok in results if ok)
    total = len(results)
    if 'logger' in globals() or 'logger' in locals():
        logger.info(f"{ f"\nSmoke summary: {passed}/{total} checks passed" }" if isinstance(f"\nSmoke summary: {passed}/{total} checks passed", str) else f"\nSmoke summary: {passed}/{total} checks passed")
    else:
        import logging
        logging.getLogger(__name__).info(f"{ f"\nSmoke summary: {passed}/{total} checks passed" }" if isinstance(f"\nSmoke summary: {passed}/{total} checks passed", str) else f"\nSmoke summary: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
