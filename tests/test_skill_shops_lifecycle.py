"""Focused, synthetic install/update/uninstall acceptance with explicit fake owner."""
import asyncio
import hashlib
import json

import pytest

from hub.skill_shops_lifecycle import SkillShopsLifecycle


def install_fixture(tmp_path):
    builtins=tmp_path/"scripts"/"skills"
    src=builtins/"test-skill"
    src.mkdir(parents=True)
    tool=src/"tool.py";tool.write_text("print('hello')\n",encoding="utf8")
    test=src/"test_tool.py";test.write_text("assert 2 + 2 == 4\n",encoding="utf8")
    root=tmp_path/"extensions"
    return builtins,src,root


def approved(plan):
    from hub.skill_shops_lifecycle import digest
    return {"allowed": True, "server_identity_verified": True,
            "owner_identity_verified": True,
            "approved_action_digest": digest(plan)}


async def _test_lifecycle_requires_protected_owner(tmp_path):
    builtins,src,root=install_fixture(tmp_path)
    lifecycle=SkillShopsLifecycle(source_root=builtins,extensions_root=root,
        quarantine=tmp_path/"quarantine",authorizer=lambda plan:{"allowed":True})
    p=lifecycle.preview("install","test-skill", chat_id="test-chat-001")
    result=await lifecycle.commit("install","test-skill",p["digest"], chat_id="test-chat-001")
    assert result["status"]=="needs_owner"
    assert not (root/"test_skill"/"manifest.json").exists()
    assert p["requires_owner_policy"]


async def _test_lifecycle_install_update_and_quarantine_only_after_owner(tmp_path):
    builtins,src,root=install_fixture(tmp_path)
    lifecycle=SkillShopsLifecycle(source_root=builtins,extensions_root=root,
        quarantine=tmp_path/"quarantine",authorizer=approved,in_use=lambda name:False)
    before=lifecycle.preview("install","test-skill", chat_id="test-chat-001")
    installed=await lifecycle.commit("install","test-skill",before["digest"], chat_id="test-chat-001")
    assert installed["status"]=="installed" and installed["functional_test_passed"]
    target=root/"test_skill"/"manifest.json"
    first=json.loads(target.read_text(encoding="utf8"))
    assert first["validated"] is True
    assert (root/"test_skill"/first["version"]/"test_tool.py").exists()

    (src/"tool.py").write_text("print('version two')\n",encoding="utf8")
    changed=lifecycle.preview("update","test-skill", chat_id="test-chat-001")
    upgraded=await lifecycle.commit("update","test-skill",changed["digest"], chat_id="test-chat-001")
    assert upgraded["status"]=="updated"
    second=json.loads(target.read_text(encoding="utf8"))
    assert second["version"]!=first["version"]
    assert hashlib.sha256((root/"test_skill"/second["version"]/"tool.py").read_bytes()).hexdigest() == second["source_sha256"]
    removal=lifecycle.preview("remove","test-skill", chat_id="test-chat-001")
    removed=await lifecycle.commit("remove","test-skill",removal["digest"], chat_id="test-chat-001")
    assert removed["status"]=="removed_to_quarantine"
    assert not (root/"test_skill").exists()
    assert (tmp_path/"quarantine").is_dir()


async def _test_lifecycle_stale_plan_and_in_use_block(tmp_path):
    builtins,src,root=install_fixture(tmp_path)
    lifecycle=SkillShopsLifecycle(source_root=builtins,extensions_root=root,
        quarantine=tmp_path/"quarantine",authorizer=approved)
    p=lifecycle.preview("install","test-skill", chat_id="test-chat-001")
    (src/"tool.py").write_text("print('unexpected modification')\n",encoding="utf8")
    with pytest.raises(ValueError,match="Stale plan"):
        await lifecycle.commit("install","test-skill",p["digest"], chat_id="test-chat-001")
    other=lifecycle.preview("install","test-skill", chat_id="test-chat-001")
    await lifecycle.commit("install","test-skill",other["digest"], chat_id="test-chat-001")
    removal=lifecycle.preview("remove","test-skill", chat_id="test-chat-001")
    blocked=await lifecycle.commit("remove","test-skill",removal["digest"], chat_id="test-chat-001")
    assert blocked["status"]=="blocked_in_use"
    assert (root/"test_skill"/"manifest.json").is_file()


def test_lifecycle_requires_protected_owner(tmp_path):
    asyncio.run(_test_lifecycle_requires_protected_owner(tmp_path))

def test_lifecycle_install_update_and_quarantine_only_after_owner(tmp_path):
    asyncio.run(_test_lifecycle_install_update_and_quarantine_only_after_owner(tmp_path))

def test_lifecycle_stale_plan_and_in_use_block(tmp_path):
    asyncio.run(_test_lifecycle_stale_plan_and_in_use_block(tmp_path))
