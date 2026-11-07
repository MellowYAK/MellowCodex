from fastapi import FastAPI
from fastapi.testclient import TestClient
from hub.development.api import router
from hub.development.service import Development
from hub.store import Store

def test_http_candidate_workflow_uses_bound_service(tmp_path):
    source=tmp_path/'project';source.mkdir()
    (source/'test_value.py').write_text('def test_value():\n assert 2 == 2\n')
    store=Store(tmp_path/'state'/'hub.sqlite3')
    task=store.create('test candidate',str(source),'code','api-candidate')
    dev=Development(store,tmp_path/'candidates')
    app=FastAPI();app.include_router(router(lambda:dev))
    with TestClient(app) as client:
        response=client.post('/api/development/create',json={'task_id':task['id']})
        assert response.status_code==200
        manifest=response.json()
        body={'task_id':task['id'],'candidate_id':manifest['id']}
        assert client.post('/api/development/inspect',json=body).json()['revision']==0
        result=client.post('/api/development/test',json={**body,'revision':0,'tests':['test_value.py']})
        assert result.status_code==200 and result.json()['verified']
        assert client.post('/api/development/test',json={**body,'revision':0,'tests':['test_value.py'],'timeout':301}).status_code==422
        other=store.create('desktop',str(source),'desktop','api-not-code')
        assert client.post('/api/development/create',json={'task_id':other['id']}).status_code==200
        readonly=store.create('inspect',str(source),'inspect','api-readonly')
        assert client.post('/api/development/create',json={'task_id':readonly['id']}).status_code==409

def test_mcp_registers_candidate_contracts_and_forwards_same_api():
    import asyncio
    from hub.development.tools import register_mcp
    class Registry:
        tools={}
        def tool(self,**kwargs):
            def register(fn):self.tools[fn.__name__]=fn;return fn
            return register
    calls=[]
    async def local(path,body,**kwargs):
        calls.append((path,body,kwargs));return {'received':True}
    registry=Registry();register_mcp(registry,local,{}, {})
    asyncio.run(registry.tools['candidate_test']('task','candidate',2,['test_a.py'],20))
    assert calls==[('/api/development/test',{'task_id':'task','candidate_id':'candidate','revision':2,'tests':['test_a.py'],'timeout':20},{'timeout':35})]
