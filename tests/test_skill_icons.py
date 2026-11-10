import base64
import io
import pytest
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hub import skill_icons as icons

def uri(raw, mime="svg+xml"):
    return "data:image/"+mime+";base64,"+base64.b64encode(raw).decode()

def test_vector_and_rejections():
    good=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#e11d48" d="M1 1h20v20H1z"/></svg>'
    assert icons.normalize_icon(uri(good)).startswith("data:image/svg+xml;base64,")
    for bad in [b'<svg><script>alert(1)</script></svg>', b'<svg onload="x()"/>',
                b'<svg><use href="https://example.com/a.svg#x"/></svg>',
                b'<svg><path fill="url(https://example.com/x)"/></svg>',
                b'<!DOCTYPE svg [<!ENTITY x "x">]><svg>&x;</svg>']:
        with pytest.raises(ValueError): icons.normalize_icon(uri(bad))
    with pytest.raises(ValueError): icons.normalize_icon("https://example.com/image.png")

def test_image_persistence_and_shared_api(tmp_path,monkeypatch):
    root=tmp_path/"extensions"; folder=root/"trial_skill";folder.mkdir(parents=True)
    (folder/"manifest.json").write_text("{}")
    monkeypatch.setattr(icons,"ROOT",tmp_path);monkeypatch.setattr(icons,"STATE",tmp_path/"state")
    b=io.BytesIO();Image.new("RGB",(600,400),"orange").save(b,format="PNG");data=uri(b.getvalue(),"png")
    app=FastAPI();app.include_router(icons.router());client=TestClient(app)
    response=client.post("/api/settings/skill-icons",json={"name":"trial_skill","data_uri":data})
    assert response.status_code==200
    saved=response.json()
    assert saved==icons.icon_settings("trial_skill")
    with Image.open(io.BytesIO(base64.b64decode(saved["icon_image"].split(",")[1]))) as image:
        assert image.size==(256,171)
    assert client.get("/api/settings/skill-icons/trial_skill").json()==saved
    assert icons.icon_settings("trial_skill",reset=True)["custom"] is False
    assert client.get("/api/settings/skill-icons/trial_skill").json()["icon_image"] is None
    assert client.post("/api/settings/skill-icons",json={"name":"missing","data_uri":data}).status_code==400
    assert client.post("/api/settings/skill-icons",json={"name":"trial_skill","data_uri":data,"reset":True}).status_code==400
