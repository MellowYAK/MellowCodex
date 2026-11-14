"""Global model settings and per-model overrides share one API."""
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from hub import model_profile_api
from hub.model_placement import load_profile_overrides, load_global


@pytest.fixture
def app_client(monkeypatch, tmp_path):
    monkeypatch.setattr(model_profile_api, "STATE", tmp_path)
    class Client(httpx.AsyncClient):
        def __init__(self, **kwargs):
            def handler(request):
                if request.url.path == "/api/tags":
                    return httpx.Response(200, json={"models":[
                        {"name":"qwen3.5:4b"},{"name":"qwen3.5:9b-q8"}]})
                return httpx.Response(404)
            super().__init__(transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(model_profile_api.httpx, "AsyncClient", Client)
    busy = {"value":False}
    app=FastAPI()
    app.include_router(model_profile_api.router(lambda: busy["value"]), prefix="/api/models")
    return TestClient(app),tmp_path,busy


def test_fresh_model_inherits_global_and_no_request_quota(app_client):
    client,_,_=app_client
    r=client.get("/api/models/profiles",params={"model":"future-model"})
    assert r.status_code==200
    p=r.json()
    assert p["global"]["active_preset"]=="automatic"
    assert p["effective"]["mode"]=="auto"
    assert p["effective"]["context_mode"]=="maximum"
    assert p["request_quota"]=="unlimited"
    assert p["provenance"]["overrides"]=={}


def test_global_preset_and_model_specific_override_do_not_leak(app_client):
    client,path,_=app_client
    assert client.post("/api/models/profiles/global",
                       json={"settings":{"active_preset":"gpu_priority"}}).json()["accepted"]
    r=client.post("/api/models/profiles/model",
                  json={"model":"qwen3.5:9b-q8","settings":{"mode":"cpu"}})
    assert r.json()["accepted"]
    a=client.get("/api/models/profiles",params={"model":"qwen3.5:9b-q8"}).json()
    b=client.get("/api/models/profiles",params={"model":"qwen3.5:4b"}).json()
    assert a["effective"]["mode"]=="cpu"
    assert a["provenance"]["field_sources"]["mode"]=="model_override"
    assert b["effective"]["mode"]=="percent"
    assert b["effective"]["gpu_percent"]==90
    assert load_global(path).active_preset=="gpu_priority"


def test_partial_edit_preserves_other_model_override_fields(app_client):
    client,path,_=app_client
    assert client.post("/api/models/profiles/model",json={"model":"qwen3.5:9b-q8",
        "settings":{"mode":"percent","gpu_percent":65}}).json()["accepted"]
    assert client.post("/api/models/profiles/model",json={"model":"qwen3.5:9b-q8",
        "settings":{"output_mode":"manual","output_tokens":9999}}).json()["accepted"]
    actual=load_profile_overrides(path)["qwen3.5:9b-q8"]
    assert actual=={"mode":"percent","gpu_percent":65,
                     "output_mode":"manual","output_tokens":9999}
    assert client.post("/api/models/profiles/model",json={"model":"qwen3.5:9b-q8",
        "clear_fields":["output_mode","output_tokens"]}).json()["accepted"]
    assert load_profile_overrides(path)["qwen3.5:9b-q8"]=={"mode":"percent","gpu_percent":65}


def test_global_partial_update_preserves_unmentioned_values(app_client):
    client,path,_=app_client
    client.post("/api/models/profiles/global",json={"settings":{
        "defaults":{"context_mode":"manual","context_tokens":8192}}})
    result=client.post("/api/models/profiles/global",json={"settings":{
        "defaults":{"output_mode":"maximum"}}}).json()
    assert result["accepted"]
    assert result["global"]["defaults"]["context_tokens"]==8192


def test_unknown_model_and_busy_state_do_not_mutate(app_client):
    client,path,busy=app_client
    assert not client.post("/api/models/profiles/model",
        json={"model":"not-installed","settings":{"mode":"cpu"}}).json()["accepted"]
    busy["value"]=True
    assert not client.post("/api/models/profiles/global",
        json={"settings":{"active_preset":"cpu_only"}}).json()["accepted"]
    assert not client.post("/api/models/profiles/model",
        json={"model":"qwen3.5:4b","settings":{"mode":"cpu"}}).json()["accepted"]
    assert not load_profile_overrides(path)
    assert load_global(path).active_preset=="automatic"
