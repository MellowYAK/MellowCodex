import asyncio
import pytest
from pydantic import ValidationError
from hub.model_settings import ModelSettings,load_settings,save_settings

def test_settings_roundtrip_and_validation(tmp_path):
    settings=ModelSettings(model='local-test',context_tokens=32768,response_tokens=512)
    save_settings(settings,tmp_path)
    assert load_settings(tmp_path)==settings
    for field,value in [('context_tokens',1000),('response_tokens',0),('request_timeout_seconds',0),('temperature',2)]:
        with pytest.raises(ValidationError):ModelSettings(**{field:value})

def test_model_request_uses_saved_configuration(monkeypatch):
    from hub.engine import Engine
    import hub.model_settings as module
    settings=ModelSettings(model='selected-model',context_tokens=32768,response_tokens=512,keep_alive_minutes=60)
    monkeypatch.setattr(module,'load_settings',lambda:settings)
    calls=[]
    class Response:
        is_error=False
        def raise_for_status(self):pass
        def json(self):return {'message':{'role':'assistant','content':'ok'}}
    class Client:
        def __init__(self,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url):
            assert url.endswith('/api/ps')
            return Response()
        async def post(self,url,json):calls.append(json);return Response()
    monkeypatch.setattr('hub.engine.httpx.AsyncClient',Client)
    asyncio.run(Engine(None).chat([],[]))
    assert calls[0]['model']=='selected-model'
    assert calls[0]['options']['num_ctx']==32768
    assert calls[0]['options']['num_predict']==512
    assert calls[0]['keep_alive']=='60m'
