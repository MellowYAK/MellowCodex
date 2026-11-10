"""Focused HTTP and MCP model settings routes using isolated state and fake runtime."""
import asyncio
import pytest
from fastapi.testclient import TestClient
from hub import app as app_module
from hub import model_preferences as control
from hub import mcp_gateway as gateway
from hub.store import Store
from hub.engine import Engine
from hub.model_settings import ModelSettings
from test_model_preferences_chat import FakeClient

@pytest.fixture
def client(tmp_path,monkeypatch):
    store=Store(tmp_path/'api.sqlite3')
    engine=Engine(store)
    monkeypatch.setattr(app_module,'store',store)
    monkeypatch.setattr(app_module,'engine',engine)
    monkeypatch.setattr(app_module,'STATE',tmp_path)
    monkeypatch.setattr(control,'STATE',tmp_path)
    monkeypatch.setattr(control.httpx,'AsyncClient',FakeClient)
    control.save_settings(ModelSettings(model='local-test'),tmp_path)
    with TestClient(app_module.app) as client:
        yield client

def test_http_model_settings_and_chat_shortcut(client,tmp_path):
    auth={'x-hub-key':app_module.TOKEN}
    response=client.get('/api/settings/model/control',headers=auth)
    assert response.status_code==200,response.text
    assert response.json()['settings']['context_tokens']==16384
    out=client.post('/api/settings/model/control',
        json={'text':'הגדל את חלון הקונטקסט ל32768'},headers=auth)
    assert out.status_code==200,out.text
    data=out.json()
    assert data['saved']==32768 and data['effective']==16384
    assert data['reload_required'] is True
    project=app_module.conversations().project(str(tmp_path))['id']
    chat=app_module.conversations().create(project)['id']
    shortcut=client.post(f'/api/chats/{chat}/messages',
        json={'text':'מה הערך הפעיל של הקונטקסט','request_id':'model-pref-read-001',
              'mode':'code'},headers=auth)
    assert shortcut.status_code==200,shortcut.text
    assert shortcut.json()['handled_model_command'] is True
    assert shortcut.json()['model_command']['saved']==32768
    invalid=client.post('/api/settings/model/control',
        json={'action':'set','field':'context_tokens','value':-1},headers=auth)
    assert invalid.json()['accepted'] is False
    assert control.load_settings(tmp_path).context_tokens==32768
    restored=client.post('/api/settings/model/control',
        json={'action':'reset','field':'context_tokens'},headers=auth)
    assert restored.json()['saved']==16384

def test_mcp_tools_call_exact_shared_api(client,monkeypatch):
    async def call(path,data=None,timeout=15):
        headers={'x-hub-key':app_module.TOKEN}
        response=(client.get(path,headers=headers) if data is None else
                  client.post(path,headers=headers,json=data))
        assert response.status_code==200,response.text
        return response.json()
    monkeypatch.setattr(gateway,'local',call)
    info=asyncio.run(gateway.model_settings_status())
    assert info['settings']['context_tokens']==16384
    result=asyncio.run(gateway.model_settings_command(text='קבע קונטקסט 32K'))
    assert result['saved']==32768
    assert result['effective']==16384
    wrong=asyncio.run(gateway.model_settings_command(text='קבע קונטקסט 64K לשיחה הזאת'))
    assert wrong['accepted'] is False and wrong['scope']=='conversation'
