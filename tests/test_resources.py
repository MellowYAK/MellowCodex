import asyncio
import httpx
import pytest
from hub.resources import Resources


def test_single_owner_and_durable_status(tmp_path):
    a=Resources(tmp_path);b=Resources(tmp_path)
    with a.owner('one','test'):
        assert a.status()['leases'][0]['state']=='active'
        with pytest.raises(ValueError):
            with b.owner('two','test'):pass
    assert a.status()['leases'][0]['state']=='released'


def test_unknown_external_model_is_not_evicted(tmp_path,monkeypatch):
    calls=[]
    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200,json={'models':[{'name':'external:latest'}]})
    client=httpx.AsyncClient
    monkeypatch.setattr('hub.resources.httpx.AsyncClient',lambda **kw:client(transport=httpx.MockTransport(handler),**kw))
    async def run():
        with pytest.raises(RuntimeError,match='externally owned'):
            async with Resources(tmp_path).inference('new','test',lambda:True):pass
    asyncio.run(run())
    assert calls==['/api/ps']


def test_switch_releases_owned_residency_without_user_disable(tmp_path,monkeypatch):
    state={'models':[{'name':'old'}],'calls':[]}
    def handler(request):
        state['calls'].append(request.url.path)
        if request.url.path=='/api/generate':state['models']=[]
        return httpx.Response(200,json={'models':state['models']})
    client=httpx.AsyncClient
    monkeypatch.setattr('hub.resources.httpx.AsyncClient',lambda **kw:client(transport=httpx.MockTransport(handler),**kw))
    async def run():
        resources=Resources(tmp_path);resources.managed('old')
        async with resources.inference('new','test',lambda:True):assert not state['models']
    asyncio.run(run())
    assert state['calls']==['/api/ps','/api/generate','/api/ps']


def test_successful_warm_inference_allows_coding_handoff(tmp_path,monkeypatch):
    state={'models':[{'name':'primary'}],'unloaded':[]}
    def handler(request):
        if request.url.path=='/api/generate':
            import json
            state['unloaded'].append(json.loads(request.content)['model'])
            state['models']=[]
        return httpx.Response(200,json={'models':state['models']})
    client=httpx.AsyncClient
    monkeypatch.setattr('hub.resources.httpx.AsyncClient',lambda **kw:client(transport=httpx.MockTransport(handler),**kw))
    async def run():
        async with Resources(tmp_path).inference('primary','agent',lambda:True):pass
        # The patch worker is another process/Resources instance sharing state.
        async with Resources(tmp_path).inference('coder','worker',lambda:True):pass
    asyncio.run(run())
    assert state['unloaded']==['primary']
