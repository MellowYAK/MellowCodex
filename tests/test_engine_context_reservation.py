"""The Ollama call uses the actual reserved output, not the configured ceiling."""
import asyncio
import copy
from contextlib import asynccontextmanager
import httpx
from hub.engine import Engine
from hub.model_settings import ModelSettings
from hub.store import Store


def test_live_chat_packet_reserves_safe_output_and_keeps_configuration(tmp_path,monkeypatch):
    settings=ModelSettings(model='unit-test',context_tokens=16000,
                           response_tokens=16000,context_management='bounded')
    monkeypatch.setattr('hub.model_settings.load_settings',lambda: settings)
    @asynccontextmanager
    async def lease(*args,**kwargs):
        yield
    monkeypatch.setattr('hub.resources.Resources.inference',lease)
    seen=[]
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url):
            return httpx.Response(200,request=httpx.Request('GET',url),
                json={'models':[{'name':'unit-test','context_length':16000}]})
        async def post(self,url,json):
            if url.endswith('/api/show'):
                return httpx.Response(200,request=httpx.Request('POST',url),json={'template':'test'})
            seen.append(json)
            return httpx.Response(200,request=httpx.Request('POST',url),
                json={'message':{'role':'assistant','content':'OK'},'done':True,'done_reason':'stop'})
    monkeypatch.setattr('hub.engine.httpx.AsyncClient',Client)
    engine=Engine(Store(tmp_path/'state.sqlite3'))
    messages=[{'role':'system','content':'Critical director instructions.'*30},
              {'role':'user','content':'Complete only this bounded step.'}]
    original=copy.deepcopy(messages)
    _,metrics=asyncio.run(engine.chat(messages,[],task_id=None))
    actual=seen[-1]['options']['num_predict']
    assert 256<=actual<16000
    assert seen[-1]['options']['num_ctx']==16000
    assert metrics['packet']['configured_response_tokens']==16000
    assert metrics['packet']['response_tokens']==actual
    assert metrics['packet']['context']['reserved_output']==actual
    assert settings.response_tokens==16000
    assert messages==original
