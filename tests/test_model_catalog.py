import asyncio
import httpx
from hub.store import Store
from hub.model_catalog import ModelCatalog


def test_verified_install_is_idempotent_and_never_loads_gpu(tmp_path,monkeypatch):
    calls=[]
    def handler(request):
        calls.append(request.url.path)
        if request.url.path=='/api/pull':return httpx.Response(200,text='{"status":"pulling","completed":2,"total":3}\n{"status":"success"}\n')
        return httpx.Response(200,json={'models':[{'name':'test:latest','digest':'sha256:abc','size':3}]})
    client=httpx.AsyncClient
    monkeypatch.setattr('hub.model_catalog.httpx.AsyncClient',lambda **kw:client(transport=httpx.MockTransport(handler),**kw))
    async def run():
        service=ModelCatalog(Store(tmp_path/'db.sqlite3'))
        job=service.submit('test:latest','stable')
        await asyncio.gather(*service.active.values())
        assert service.jobs()[0]['state']=='ready'
        assert service.submit('test:latest','stable')['id']==job['id']
        assert '/api/generate' not in calls and '/api/chat' not in calls
        assert calls.count('/api/pull')==1
    asyncio.run(run())


def test_cancellation_before_start_and_restart_are_explicit(tmp_path):
    async def run():
        service=ModelCatalog(Store(tmp_path/'db.sqlite3'))
        job=service.submit('test:latest','cancel')
        assert (await service.cancel(job['id']))['state']=='interrupted'
        assert not service.active
        job=service.submit('test:latest','resume')
        assert job['id']!=service.jobs()[1]['id']
        await service.close()
        service.recover()
        assert all(j['state']=='interrupted' for j in service.jobs())
    asyncio.run(run())


def test_resident_status_is_available_to_local_model_group():
    from hub.tools import ToolRunner
    runner=ToolRunner.__new__(ToolRunner)
    runner.enabled_tool_groups={'task':{'models'}}
    runner.application_targets={}
    for mode in ('code','desktop'):
        names={t['function']['name'] for t in runner.catalog(mode,'task')}
        assert 'model_memory_status' in names
