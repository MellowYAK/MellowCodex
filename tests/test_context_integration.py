import asyncio
import json
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hub.context.api import router
from hub.context.tools import register_mcp
from hub.context.runtime import prepare
from hub.context import ProjectContext
from hub.store import Store
from hub.conversations import Conversations

def service(tmp_path):
    root=tmp_path/'project';root.mkdir();(root/'a.py').write_text('def total(): return 42\n')
    store=Store(tmp_path/'state'/'hub.sqlite3');conversations=Conversations(store)
    p=conversations.project(str(root))
    return ProjectContext(tmp_path/'state',conversations),p,store

def test_http_and_mcp_share_annotations_and_hash_handles(tmp_path):
    svc,p,store=service(tmp_path);app=FastAPI();app.include_router(router(lambda:svc));client=TestClient(app)
    funcs={}
    class MCP:
        def tool(self,**kw):
            def register(fn):funcs[fn.__name__]=fn;return fn
            return register
    async def local(path,data,timeout=15):
        response=client.post(path,json=data);assert response.status_code==200;return response.json()
    register_mcp(MCP(),local,None,None)
    async def run():
        await funcs['context_refresh'](p['id'])
        saved=await funcs['context_annotate'](p['id'],'a.py',aliases=['סכום'],must_not_break=['signature'])
        assert saved['saved']
        data=client.post('/api/context/search',json={'project_id':p['id'],'query':'סכום'}).json()
        ref=data['results'][0]['ref']
        assert '42' in (await funcs['context_expand'](p['id'],ref))['text']
        assert (await funcs['project_context'](p['id']))['annotations'][0]['payload']['must_not_break']==['signature']
    asyncio.run(run())
    assert client.post('/api/context/search',json={'project_id':p['id'],'limit':999}).status_code==422

def test_bootstrap_records_actual_reads_but_does_not_hide_failure(tmp_path):
    svc,p,store=service(tmp_path)
    task=store.create('inspect source',p['path'],'code','test')
    class Runner:
        async def execute(self,task,name,args):
            return svc.refresh(p['id']) if name=='context_refresh' else svc.overview(p['id'])
    messages=[{'role':'system','content':'base'},{'role':'user','content':'goal'}]
    asyncio.run(prepare(SimpleNamespace(store=store,runner=Runner()),task,messages))
    actions=store.actions(task['id'])
    assert [a['tool'] for a in actions]==['project_context','context_refresh','project_context']
    assert actions[1]['result']['indexed']==1

def test_existing_index_does_not_rescan_on_new_code_task(tmp_path):
    svc,p,store=service(tmp_path);svc.refresh(p['id'])
    task=store.create('inspect existing source',p['path'],'code','existing-index')
    class Runner:
        async def execute(self,task,name,args):
            assert name!='context_refresh','New task must not force full project scan'
            return svc.overview(p['id'])
    messages=[{'role':'system','content':'base'},{'role':'user','content':'goal'}]
    asyncio.run(prepare(SimpleNamespace(store=store,runner=Runner()),task,messages))
    assert store.actions(task['id'])[0]['result']['index']['revision']==1
    assert json.loads(messages[-1]['content'])['paths']==['a.py']

def test_required_constraints_stay_in_fixed_model_packet(tmp_path):
    from hub.model_context import prepare_messages
    svc,p,store=service(tmp_path)
    svc.annotate(p['id'],'a.py',notes='x'*6000,must_not_break=['KEEP_SIGNATURE_42'])
    task=store.create('inspect source',p['path'],'code','test')
    class Runner:
        async def execute(self,task,name,args):
            return svc.refresh(p['id']) if name=='context_refresh' else svc.overview(p['id'])
    messages=[{'role':'system','content':'base'},{'role':'user','content':'goal'}]
    asyncio.run(prepare(SimpleNamespace(store=store,runner=Runner()),task,messages))
    for i in range(20):
        messages.extend([{'role':'assistant','content':'next'}, {'role':'tool','content':json.dumps({'text':'recent '*100})}])
    packet=prepare_messages(messages,[],4096,512)
    assert 'KEEP_SIGNATURE_42' in packet[0]['content']

def test_recovery_exposes_uncertain_actions_without_replay(tmp_path):
    svc,p,store=service(tmp_path);chat=svc.conversations.create(p['id'])
    task=svc.conversations.submit(chat['id'],'change code','code','test')
    action=store.begin_action(task['id'],'write_file',{'path':'a.py','content':'uncertain'})
    result=svc.recovery(p['id'])
    assert result['uncertain_actions'][0]['action_id']==action
    assert not result['replayed'] and store.actions(task['id'])[0]['state']=='pending'
