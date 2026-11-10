"""Negative Skill Shops lifecycle safety tests. No real owner grant is issued."""
import asyncio
import json
import sqlite3

import pytest

from hub.skill_shops_lifecycle import SkillShopsLifecycle, digest


def _approved(plan):
    return {
        "allowed": True, "server_identity_verified": True,
        "owner_identity_verified": True,
        "approved_action_digest": digest(plan),
    }


def _fixture(tmp_path, authorizer=None):
    folder = tmp_path / "scripts" / "skills" / "test-skill"
    folder.mkdir(parents=True)
    (folder / "tool.py").write_text("print('hello')\n", encoding="utf8")
    (folder / "test_tool.py").write_text("assert True\n", encoding="utf8")
    return SkillShopsLifecycle(
        source_root=folder.parent, extensions_root=tmp_path / "installed",
        quarantine=tmp_path / "quarantine",
        authorizer=authorizer or _approved,
        in_use=lambda _: False,
    ), folder


def test_existing_target_without_manifest_never_overwritten(tmp_path):
    lifecycle, folder = _fixture(tmp_path)
    orphan = tmp_path / "installed" / "test_skill"
    orphan.mkdir(parents=True)
    (orphan / "keep.txt").write_text("preserve", encoding="utf8")
    with pytest.raises(ValueError, match="Target exists"):
        lifecycle.preview("install", "test-skill", chat_id="test-chat-001")
    assert (orphan / "keep.txt").read_text(encoding="utf8") == "preserve"


def test_source_changed_during_authorization_is_rejected(tmp_path):
    lifecycle, folder = _fixture(tmp_path)
    def mutate_source_after_approval(plan):
        (folder / "tool.py").write_text("print('unreviewed')\n", encoding="utf8")
        return _approved(plan)
    lifecycle.authorizer = mutate_source_after_approval
    plan = lifecycle.preview("install", "test-skill", chat_id="test-chat-001")
    result = asyncio.run(lifecycle.commit("install", "test-skill", plan["digest"], chat_id="test-chat-001"))
    assert result["status"] == "stale_after_authorization"
    assert not (tmp_path / "installed" / "test_skill" / "manifest.json").exists()


def test_original_source_coverage_cannot_be_removed(tmp_path):
    lifecycle, folder = _fixture(tmp_path)
    proposal = lifecycle.preview("install", "test-skill", chat_id="test-chat-001")
    result = asyncio.run(lifecycle.commit("install", "test-skill", proposal["digest"], chat_id="test-chat-001"))
    assert result["status"] == "installed"
    p = tmp_path / "installed" / "test_skill" / "manifest.json"
    manifest = json.loads(p.read_text(encoding="utf8"))
    manifest["capability_ids"] = ["research100.045"]
    p.write_text(json.dumps(manifest), encoding="utf8")
    deletion = lifecycle.preview("remove", "test-skill", chat_id="test-chat-001")
    answer = asyncio.run(lifecycle.commit("remove", "test-skill", deletion["digest"], chat_id="test-chat-001"))
    assert answer["status"] == "blocked_coverage"
    assert p.is_file()


def test_installed_shop_removal_gate_checks_active_tasks(tmp_path, monkeypatch):
    from hub import config
    from hub.skill_shops import _extension_tasks_busy
    monkeypatch.setattr(config, "STATE", tmp_path)
    db = tmp_path / "hub.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE tasks (state TEXT NOT NULL)")
        conn.execute("CREATE TABLE actions (args TEXT,state TEXT)")
        conn.execute("INSERT INTO tasks VALUES ('running')")
    assert _extension_tasks_busy("trial")
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE tasks SET state = 'done'")
    assert not _extension_tasks_busy("trial")
    monkeypatch.setattr(config, "STATE", tmp_path / "missing")
    assert _extension_tasks_busy("trial")


def test_history_does_not_lock_unrelated_packages(tmp_path, monkeypatch):
    from contextlib import closing
    from hub import config
    from hub.skill_shops import _extension_tasks_busy
    monkeypatch.setattr(config, "STATE", tmp_path)
    with closing(sqlite3.connect(tmp_path / "hub.sqlite3")) as db:
        db.executescript("CREATE TABLE tasks (state TEXT); CREATE TABLE actions (args TEXT,state TEXT); INSERT INTO tasks VALUES ('waiting_review');")
        db.commit()
        assert not _extension_tasks_busy("shop_demo")
        db.execute("INSERT INTO actions VALUES (?, 'pending')", ('{"name":"shop_demo"}',))
        db.commit()
        assert _extension_tasks_busy("shop_demo")
