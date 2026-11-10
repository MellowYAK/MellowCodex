"""HTTP tests for the reviewed-local Skill Shops lifecycle. Never grant owner access."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import hub.skill_shops as shop
from hub.skill_shops_lifecycle import SkillShopsLifecycle


def test_http_installer_requires_separate_owner_approval(tmp_path, monkeypatch):
    source = tmp_path / "scripts" / "skills" / "test-package"
    source.mkdir(parents=True)
    (source / "tool.py").write_text("print('trial')\n", encoding="utf8")
    (source / "test_tool.py").write_text("assert True\n", encoding="utf8")
    installed = tmp_path / "extensions"

    # This deliberately lacks an authenticated owner consent response.
    lifecycle = SkillShopsLifecycle(
        source_root=source.parent,
        extensions_root=installed,
        quarantine=tmp_path / "quarantine",
        authorizer=lambda req: {
            "ok": True, "server_identity_verified": True, "allowed": True
        },
        in_use=lambda name: False,
    )
    monkeypatch.setattr(shop, "_marketplace", lifecycle)
    monkeypatch.setattr(shop, "_require_chat", lambda chat: None)
    app = FastAPI()
    app.include_router(shop.action_router())
    app.include_router(shop.router())
    with TestClient(app) as client:
        available = client.get("/api/skill-shops/available")
        assert available.status_code == 200
        assert available.json()["packages"][0]["slug"] == "test-package"
        p = client.post("/api/skill-shops/preview", json={
            "chat_id": "test-chat-001", "action": "install", "slug": "test-package"
        })
        assert p.status_code == 200 and p.json()["executed"] is False
        commit = client.post("/api/skill-shops/commit", json={
            "chat_id": "test-chat-001", "action": "install", "slug": "test-package",
            "expected_digest": p.json()["digest"]
        })
        assert commit.status_code == 200
        assert commit.json()["status"] == "needs_owner"
        assert not (installed / "test_package" / "manifest.json").exists()


def test_http_rejects_unknown_path_and_stale_digest(tmp_path, monkeypatch):
    lifecycle = SkillShopsLifecycle(
        source_root=tmp_path / "sources",
        extensions_root=tmp_path / "installed",
        quarantine=tmp_path / "trash",
        authorizer=lambda req: {"allowed": False},
    )
    monkeypatch.setattr(shop, "_marketplace", lifecycle)
    monkeypatch.setattr(shop, "_require_chat", lambda chat: None)
    app = FastAPI()
    app.include_router(shop.action_router())
    app.include_router(shop.router())
    with TestClient(app) as client:
        bad = client.post("/api/skill-shops/preview", json={
            "chat_id": "test-chat-001", "action": "install", "slug": "../escape"
        })
        assert bad.status_code == 409
        invalid = client.post("/api/skill-shops/commit", json={
            "chat_id": "test-chat-001", "action": "remove", "slug": "not_installed",
            "expected_digest": "0" * 64
        })
        assert invalid.status_code == 409
