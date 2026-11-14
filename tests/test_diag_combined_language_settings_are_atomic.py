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

def test_combined_language_settings_are_atomic(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'STATE',tmp_path)
    monkeypatch.setattr(service.httpx,'AsyncClient',FakeClient)
    service.save_settings(ModelSettings(model='local-test'),tmp_path)
    for command in ('הגדר את שניהם ל־16000','Set context and response tokens to 16000'):
        parsed=parse_model_command(command)
        assert parsed['action']=='set_many'
        assert parsed['fields']=={'context_tokens':16000,'response_tokens':16000}
        outcome=asyncio.run(service.perform(text=command))
        assert outcome['accepted'] is True, outcome
        assert outcome['saved']=={'context_tokens':16000,'response_tokens':16000}
    assert service.load_settings(tmp_path).context_tokens==16000
    assert service.load_settings(tmp_path).response_tokens==16000
    rejected=asyncio.run(service.perform(text='הגדר את שניהם ל־16001'))
    assert rejected['accepted'] is False
    assert service.load_settings(tmp_path).response_tokens==16000
    rejected_busy=asyncio.run(service.perform(text='Set context and response tokens to 16000',busy=True))
    assert rejected_busy['accepted'] is False
