import hashlib
import json
from pathlib import Path
from hub.skill_shops import catalog_data, router

def test_catalog_hash_and_capabilities(tmp_path):
    root=tmp_path/"extensions";folder=root/"trial_skill";version="a"*32
    (folder/version).mkdir(parents=True)
    data=b"print(1)"
    (folder/version/"tool.py").write_bytes(data)
    (folder/"manifest.json").write_text(json.dumps({
        "name":"trial_skill","version":version,
        "source_sha256":hashlib.sha256(data).hexdigest(),
        "capability_ids":["research100.001","research100.001","research100.002"],
        "categories":["Windows"],"description":"Local test"}),encoding="utf8")
    audit=tmp_path/"audit.json"
    audit.write_text(json.dumps({"items":[{"source_id":"research100.001","live_verification":"live_isolated_trial","full_real_world_acceptance":False}]}),encoding="utf8")
    info=catalog_data(extension_root=root,audit_path=audit)
    assert info["installed_skills"]==1 and info["mapped_capabilities"]==2
    assert info["skills"][0]["integrity_verified"] is True
    assert info["skills"][0]["capabilities"][0]["verification"]=="live_isolated_trial"
    assert info["install_enabled"] and info["uninstall_enabled"]
    assert info["fully_verified"]==0
    (folder/version/"tool.py").write_text("tampered",encoding="utf8")
    assert catalog_data(extension_root=root,audit_path=audit)["skills"][0]["integrity_verified"] is False

def test_catalog_get_only():
    routes=router().routes
    assert {r.path for r in routes}=={"/api/skill-shops","/api/skill-shops/{name}"}
    assert all(r.methods=={"GET"} for r in routes)

def test_real_extensions_read_only_when_present():
    from hub.config import ROOT
    root=ROOT/"extensions"
    if not root.is_dir() or len(list(root.glob("*/manifest.json")))<20:
        import pytest
        pytest.skip("Real Windows skill registry not mounted in this test environment")
    item=catalog_data()
    assert item["installed_skills"]>=20
    assert item["mapped_capabilities"]==100
    assert len({c["id"] for s in item["skills"] for c in s["capabilities"]})==100
    assert all(s["integrity_verified"] for s in item["skills"])
    assert item["fully_verified"]<100
    assert item["install_enabled"] and item["uninstall_enabled"]

def test_frontend_has_usable_catalog_controls():
    from hub.skill_shops import NAME
    import subprocess, shutil
    source=Path(__file__).resolve().parents[1]/"hub"/"static"/"shell.js"
    text=source.read_text(encoding="utf8")
    assert "api('/skill-shops')" in text
    assert "shop" in text.lower()
    assert "search.addEventListener" in text
    assert "details" in text
    if shutil.which("node"):
        result=subprocess.run(["node","--check",str(source)],capture_output=True,text=True,timeout=15)
        assert result.returncode==0,result.stderr
