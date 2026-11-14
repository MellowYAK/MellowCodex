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
