"""Focused, no-Ollama-network settings acceptance; no user state changes."""
import asyncio
import pytest
from hub import model_preferences as service
from hub.model_settings import ModelSettings,parse_model_command,field_metadata

class Response:
    def __init__(self,payload):self.payload=payload
    def raise_for_status(self):pass
    def json(self):return self.payload

class FakeClient:
    def __init__(self,**kwargs):pass
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def get(self,url):
        if url.endswith('/api/ps'):
            return Response({'models':[{'name':'local-test','context_length':16384}]})
        if url.endswith('/api/tags'):
            return Response({'models':[{'name':'local-test'}]})
        raise AssertionError(url)
    async def post(self,url,json):
        if url.endswith('/api/show'):
            return Response({'model_info':{'general.context_length':262144}})
        raise AssertionError(url)

def test_busy_rejects_settings_mutation(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'STATE',tmp_path)
    monkeypatch.setattr(service.httpx,'AsyncClient',FakeClient)
    service.save_settings(ModelSettings(model='local-test'),tmp_path)
    outcome=asyncio.run(service.perform(action='set',field='temperature',value=.5,busy=True))
    assert outcome['accepted'] is False
    assert service.load_settings(tmp_path).temperature==.1
