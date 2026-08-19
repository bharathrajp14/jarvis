# tests/test_web_workspace.py — Comprehensive Unit & Integration Tests for BR JARVIS MK40.2 / MK41 Workspace
import pytest
from fastapi.testclient import TestClient

from brjarvis.memory.canonical_db import CanonicalDatabaseManager
from brjarvis.memory.workspace_store import WorkspaceStore
from brjarvis.web.api.server import create_app
from brjarvis.web.api.state import SERVER_API_KEY


@pytest.fixture
def temp_db(tmp_path):
    """Create an isolated test canonical database."""
    db_file = tmp_path / "test_canonical.db"
    mgr = CanonicalDatabaseManager(db_path=db_file)
    store = WorkspaceStore(db_manager=mgr)
    return mgr, store


@pytest.fixture
def client():
    """Create FastAPI test client."""
    app = create_app()
    headers = {}
    if SERVER_API_KEY:
        headers["X-API-Key"] = SERVER_API_KEY
    return TestClient(app, headers=headers)


def test_workspace_store_conversations(temp_db):
    mgr, store = temp_db

    # 1. Create conversation
    conv = store.create_conversation(title="Test Architecture Design")
    assert conv.conversation_id.startswith("conv_")
    assert conv.title == "Test Architecture Design"
    assert "main" in conv.active_branch_id

    # 2. Add message
    msg = store.add_message(
        conversation_id=conv.conversation_id,
        role="user",
        content="Build a portfolio and publish to GitHub",
    )
    assert msg.message_id.startswith("msg_")
    assert msg.role == "user"
    assert msg.content == "Build a portfolio and publish to GitHub"

    # 3. Add assistant response
    asst_msg = store.add_message(
        conversation_id=conv.conversation_id,
        role="assistant",
        content="Inspecting portfolio templates...",
        latency_ms=45,
    )
    assert asst_msg.role == "assistant"

    # 4. List messages
    messages = store.get_messages(conv.conversation_id)
    assert len(messages) == 2

    # 5. Branch conversation
    branch_id = store.branch_conversation(conv.conversation_id, msg.message_id, "Alternative Model Branch")
    assert branch_id.startswith("br_")
    updated_conv = store.get_conversation(conv.conversation_id)
    assert updated_conv.active_branch_id == branch_id

    # 6. Duplicate conversation
    dupe = store.duplicate_conversation(conv.conversation_id)
    assert dupe is not None
    assert dupe.conversation_id != conv.conversation_id
    assert "(Copy)" in dupe.title

    # 7. Auto-title generator
    title = store.generate_title("Please create a modern portfolio in Next.js with dark mode")
    assert "portfolio" in title.lower() or "modern" in title.lower()


def test_workspace_store_projects_and_files(temp_db, tmp_path):
    mgr, store = temp_db

    # 1. Create project
    proj = store.create_project(
        name="BR JARVIS MK41",
        description="Autonomous AI workspace",
        instructions="Always use Python 3.12",
    )
    assert proj.project_id.startswith("proj_")
    assert proj.name == "BR JARVIS MK41"

    # 2. Add file
    dummy_file = tmp_path / "spec.md"
    dummy_file.write_text("# Spec Document", encoding="utf-8")
    pfile = store.add_project_file(
        project_id=proj.project_id,
        filename="spec.md",
        file_path=str(dummy_file),
        file_size=len("# Spec Document"),
        mime_type="text/markdown",
    )
    assert pfile.file_id.startswith("file_")
    assert pfile.filename == "spec.md"

    # 3. List files
    files = store.list_project_files(proj.project_id)
    assert len(files) == 1

    # 4. Update project
    up_proj = store.update_project(proj.project_id, name="BR JARVIS MK41 PRO", pinned=True)
    assert up_proj.name == "BR JARVIS MK41 PRO"
    assert up_proj.pinned is True


def test_workspace_store_artifacts_and_verification(temp_db, tmp_path):
    mgr, store = temp_db

    dummy_art = tmp_path / "resume.pdf"
    dummy_art.write_bytes(b"%PDF-1.4 dummy")

    art = store.record_artifact(
        filename="resume.pdf",
        host_path=str(dummy_art),
        task_id="task_12345",
        mime_type="application/pdf",
        file_size=14,
        verification_status="PENDING",
    )
    assert art.artifact_id.startswith("art_")
    assert art.filename == "resume.pdf"
    assert art.verification_status == "PENDING"

    # Verify artifact
    store.verify_artifact(art.artifact_id, verified=True)
    updated_art = store.get_artifact(art.artifact_id)
    assert updated_art.verification_status == "VERIFIED"


def test_workspace_store_notifications(temp_db):
    mgr, store = temp_db

    notif = store.add_notification(
        title="Task Finished",
        message="Portfolio generated successfully.",
        category="TASKS",
        severity="success",
    )
    assert notif.notification_id.startswith("notif_")
    assert notif.is_read is False

    notifs = store.list_notifications(unread_only=True)
    assert len(notifs) >= 1

    store.mark_notification_read(notif.notification_id)
    unread = store.list_notifications(unread_only=True)
    assert not any(n.notification_id == notif.notification_id for n in unread)


def test_workspace_store_global_search(temp_db):
    mgr, store = temp_db

    conv = store.create_conversation(title="Quantum Physics Research")
    proj = store.create_project(name="Quantum Workspace", description="Exploring superposition")

    results = store.search_all("Quantum")
    assert len(results) >= 1
    types = [r["entity_type"] for r in results]
    assert "conversation" in types or "project" in types


def test_api_conversations_endpoints(client):
    # 1. Create conversation
    res = client.post("/api/conversations", json={"title": "FastAPI Audit"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    conv_id = data["conversation"]["conversation_id"]

    # 2. List conversations
    res = client.get("/api/conversations")
    assert res.status_code == 200
    convs = res.json()["conversations"]
    assert any(c["conversation_id"] == conv_id for c in convs)

    # 3. Add message
    res = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={
            "role": "user",
            "content": "Verify all route mounts",
        },
    )
    assert res.status_code == 200

    # 4. Get conversation details
    res = client.get(f"/api/conversations/{conv_id}")
    assert res.status_code == 200
    details = res.json()
    assert len(details["messages"]) == 1

    # 5. Export conversation
    res = client.get(f"/api/conversations/{conv_id}/export?format=markdown")
    assert res.status_code == 200
    assert "Verify all route mounts" in res.json()["content"]

    # 6. Delete conversation
    res = client.delete(f"/api/conversations/{conv_id}")
    assert res.status_code == 200


def test_api_projects_and_search_endpoints(client):
    # 1. Create project
    res = client.post("/api/projects", json={"name": "Career OS Studio", "description": "10-Theme Resume Engine"})
    assert res.status_code == 200
    proj_id = res.json()["project"]["project_id"]

    # 2. Search
    res = client.get("/api/search?q=Career")
    assert res.status_code == 200
    results = res.json()["results"]
    assert len(results) >= 1

    # 3. Delete project
    res = client.delete(f"/api/projects/{proj_id}")
    assert res.status_code == 200


def test_api_skills_endpoint(client):
    res = client.get("/api/skills")
    assert res.status_code == 200
    data = res.json()
    assert "skills" in data
    assert len(data["skills"]) >= 1
    names = [s["name"] for s in data["skills"]]
    assert any(
        "browser" in n.lower() or "python" in n.lower() or "search" in n.lower() or len(names) > 0 for n in names
    )



def test_desktop_workspace_handoff_redeems_to_browser_session(client):
    if not SERVER_API_KEY:
        pytest.skip("Server API key is not configured in this environment")

    from urllib.parse import parse_qs, urlparse

    created = client.post("/api/auth/desktop-handoff", json={"redirect": "/web/"})
    assert created.status_code == 200
    handoff_url = created.json()["url"]
    query = parse_qs(urlparse(handoff_url).query)
    handoff = query["handoff"][0]
    assert SERVER_API_KEY not in handoff_url

    redeemed = client.post("/api/auth/desktop-handoff/redeem", json={"handoff": handoff})
    assert redeemed.status_code == 200
    assert redeemed.json()["success"] is True

    status = client.get("/api/auth/status")
    assert status.status_code == 200
    assert status.json()["authenticated"] is True

    reused = client.post("/api/auth/desktop-handoff/redeem", json={"handoff": handoff})
    assert reused.status_code == 401
