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

def test_natural_language_and_scope():
    parsed=parse_model_command('הגדל את חלון הקונטקסט של המודל המקומי ל32768')
    assert parsed=={'action':'set','field':'context_tokens','scope':'default','value':32768}
    parsed=parse_model_command('קבע חלון קונטקסט 64K לשיחה הזאת')
    assert parsed['value']==65536 and parsed['scope']=='conversation'
    assert parse_model_command('מה הערך הפעיל של הקונטקסט')['action']=='get'
    assert parse_model_command('קבע64K לשיחה הזאת')['scope']=='conversation'
    assert parse_model_command('מה הערך הפעיל?')['field']=='context_tokens'
    assert parse_model_command('החזר לברירת המחדל')['action']=='reset'
    assert parse_model_command('החזר את הקונטקסט לברירת המחדל')['action']=='reset'
    assert 'maximum' not in field_metadata()['context_tokens']
    assert field_metadata()['context_tokens']['units']=='tokens'

def test_typed_change_runtime_and_restore(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'STATE',tmp_path)
    monkeypatch.setattr(service.httpx,'AsyncClient',FakeClient)
    service.save_settings(ModelSettings(model='local-test'),tmp_path)
    first=asyncio.run(service.perform(text='הגדל את חלון הקונטקסט ל32768'))
    assert first['accepted'] is True
    assert first['saved']==32768
    assert first['effective']==16384
    assert first['reload_required'] is True
    assert service.load_settings(tmp_path).context_tokens==32768
    rejected=asyncio.run(service.perform(text='קבע חלון קונטקסט 64K לשיחה הזאת'))
    assert rejected['accepted'] is False and rejected['scope']=='conversation'
    assert service.load_settings(tmp_path).context_tokens==32768
    bad=asyncio.run(service.perform(action='set',field='context_tokens',value='not-a-number'))
    assert bad['accepted'] is False and service.load_settings(tmp_path).context_tokens==32768
    restored=asyncio.run(service.perform(text='החזר את הקונטקסט לברירת המחדל'))
    assert restored['accepted'] is True and restored['saved']==16384
    assert service.load_settings(tmp_path).context_tokens==16384
    other=asyncio.run(service.perform(action='set',field='response_tokens',value=512))
    assert other['accepted'] is True and other['saved']==512
    assert service.load_settings(tmp_path).response_tokens==512

def test_busy_rejects_settings_mutation(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'STATE',tmp_path)
    monkeypatch.setattr(service.httpx,'AsyncClient',FakeClient)
    service.save_settings(ModelSettings(model='local-test'),tmp_path)
    outcome=asyncio.run(service.perform(action='set',field='temperature',value=.5,busy=True))
    assert outcome['accepted'] is False
    assert service.load_settings(tmp_path).temperature==.1

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
