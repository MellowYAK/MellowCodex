import asyncio, json
import pytest
from hub import skill_shops_lifecycle as mod

def fixture(tmp_path):
    source=tmp_path/"sources"/"trial-skill";source.mkdir(parents=True)
    (source/"tool.py").write_text("VALUE=1\n")
    (source/"test_tool.py").write_text("import tool\nassert tool.VALUE==1\n")
    def allow(plan):
        return {"allowed":True,"server_identity_verified":True,"approved_action_digest":mod.digest(plan)}
    service=mod.SkillShopsLifecycle(source_root=source.parent,extensions_root=tmp_path/"installed",
        quarantine=tmp_path/"backup",authorizer=allow,in_use=lambda _:False)
    return service,source
def run(service,action):
    plan=service.preview(action,"trial-skill","test-chat-001")
    return asyncio.run(service.commit(action,"trial-skill",plan["digest"],"test-chat-001"))

def test_failed_update_preserves_entire_manifest(tmp_path):
    s,src=fixture(tmp_path)
    assert run(s,"install")["executed"]
    manifest=s.extensions_root/"trial_skill"/"manifest.json"
    before=manifest.read_bytes()
    (src/"tool.py").write_text("VALUE=2\n")
    assert run(s,"update")["status"]=="validation_failed"
    assert manifest.read_bytes()==before

def test_mutating_test_snapshot_cannot_be_published(tmp_path):
    s,src=fixture(tmp_path)
    (src/"test_tool.py").write_text("from pathlib import Path\nPath('tool.py').write_text('VALUE=99')\n")
    assert run(s,"install")["status"]=="snapshot_changed"
    assert not (s.extensions_root/"trial_skill").exists()

def test_full_policy_binding_and_safe_denial(monkeypatch):
    plan={"chat_id":"test-chat-001","action":"install","installed_name":"trial_skill"}
    state={"installed":True,"server_identity_verified":True,"policy_revision":7,"effective":"full"}
    monkeypatch.setattr(mod,"owner_status",lambda chat:state)
    def reply(req):
        assert req["command"]=="authorize" and req["policy_revision"]==7
        return {"ok":True,"allowed":True,"server_identity_verified":True,"binding":mod.digest(req),"policy_revision":7}
    monkeypatch.setattr(mod,"authorize_action",reply)
    assert mod.protected_authorize(plan)["allowed"]
    state["effective"]="safe"
    assert not mod.protected_authorize(plan)["allowed"]
    state["effective"]="full"
    monkeypatch.setattr(mod,"authorize_action",lambda req:{"ok":True,"allowed":True,"server_identity_verified":True,"binding":"0"*64,"policy_revision":7})
    assert not mod.protected_authorize(plan)["allowed"]

def test_ask_uses_consumed_exact_owner_decision(monkeypatch):
    monkeypatch.setattr(mod,"owner_status",lambda chat:{"installed":True,"server_identity_verified":True,"policy_revision":4,"effective":"ask"})
    monkeypatch.setattr(mod,"authorize_action",lambda req:{"ok":True,"allowed":True,"server_identity_verified":True,"request_id":mod.digest(req),"policy_revision":4,"reason":"owner_approved"})
    assert mod.protected_authorize({"chat_id":"test-chat-001","action":"remove","installed_name":"trial_skill"})["allowed"]

def test_no_chat_and_path_escape_rejected(tmp_path):
    s,_=fixture(tmp_path)
    with pytest.raises(ValueError):s.preview("install","trial-skill")
    with pytest.raises(ValueError):s.preview("install","../escape","test-chat-001")

def test_update_blocked_while_in_use(tmp_path):
    s,_=fixture(tmp_path);run(s,"install");s.in_use=lambda _:True
    assert run(s,"update")["status"]=="blocked_in_use"
