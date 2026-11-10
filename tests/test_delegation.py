import asyncio
import json
import pytest
import httpx
from hub.store import Store, Conflict
from hub.conversations import Conversations
from hub.delegation import Delegation


def setup(tmp_path):
    store=Store(tmp_path/'hub.db');chats=Conversations(store)
    project=chats.project(str(tmp_path));chat=chats.create(project['id'])
    svc=Delegation(store)
    svc.save_profile(dict(id='director',provider='chatgpt',name='Director',transport='mcp'))
    svc.save_profile(dict(id='worker',provider='custom',name='Worker',transport='api',model='test',endpoint='http://127.0.0.1:9999/v1'))
    run=svc.start(chat['id'],'test-request','Map project','director')
    return store,svc,run


def test_director_gates_persistence_and_dispatch(tmp_path):
    store,svc,r=setup(tmp_path)
    assert len(svc.catalog()['providers'])==72
    r=svc.update(r['id'],r['revision'],'assign',{'worker':{'id':'worker'},'instruction':'Read project map'})
    w=r['workers'][0]['id']
    with pytest.raises(Conflict):svc.dispatch(r['id'],r['revision'],'Read map',['project_brief'],context_read={'operation':'brief'})
    with pytest.raises(Conflict):svc.update(r['id'],0,'result',{'worker_id':w,'result':'proposal'})
    r=svc.update(r['id'],r['revision'],'result',{'worker_id':w,'result':'Read the map before edits'})
    r=svc.update(r['id'],r['revision'],'review',{'worker_id':w,'decision':'approved','feedback':'Read-only scoped proposal accepted'})
    assert r['state']=='ready_for_execution'
    assert Delegation(Store(tmp_path/'hub.db')).status(r['id'])['workers'][0]['result']=='Read the map before edits'
    task=svc.dispatch(r['id'],r['revision'],'Read project map',['project_brief'],context_read={'operation':'brief'})
    svc.guard(task['id'])
    r=svc.status(r['id'])
    with pytest.raises(Conflict):svc.update(r['id'],r['revision'],'complete',{})
    assert len(Conversations(store).get(r['chat_id'])['turns'])==1


def test_parallel_proposals_and_dependency_gate(tmp_path,monkeypatch):
    store,svc,r=setup(tmp_path)
    r=svc.update(r['id'],r['revision'],'assign',{'worker':{'id':'worker'},'instruction':'First'})
    first=r['workers'][0]['id']
    r=svc.update(r['id'],r['revision'],'assign',{'worker':{'id':'worker'},'instruction':'Second'})
    r=svc.update(r['id'],r['revision'],'assign',{'worker':{'id':'worker'},'instruction':'Dependent','dependencies':[first]})
    active=0;peak=0
    async def post(self,url,**kwargs):
        nonlocal active,peak
        assert 'tools' not in kwargs['json']
        active+=1;peak=max(peak,active)
        await asyncio.sleep(.01)
        active-=1
        return httpx.Response(200,json={'choices':[{'message':{'content':'Observed proposal'}}]})
    monkeypatch.setattr(httpx.AsyncClient,'post',post)
    result=asyncio.run(svc.run_workers(r['id']))
    assert peak==2
    assert [w['state'] for w in result['workers']]==['waiting_review','waiting_review','assigned']
    assert not result['execution_task_id']
    with pytest.raises(Conflict):svc.update(r['id'],result['revision'],'result',{'worker_id':result['workers'][2]['id'],'result':'Premature'})


def test_no_credentials_in_profiles_and_errors(tmp_path,monkeypatch):
    _,svc,r=setup(tmp_path)
    with pytest.raises(ValueError):svc.save_profile(dict(id='bad',provider='custom',name='Bad',transport='api',model='x',endpoint='https://secret@example.com/v1'))
    r=svc.update(r['id'],r['revision'],'assign',{'worker':{'id':'worker'},'instruction':'Test failure'})
    async def post(*args,**kwargs):return httpx.Response(401,text='private token should not leak')
    monkeypatch.setattr(httpx.AsyncClient,'post',post)
    result=asyncio.run(svc.run_workers(r['id']))
    assert result['workers'][0]['result']=='Provider HTTP 401'
    assert 'private token' not in json.dumps(result)
