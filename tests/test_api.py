import pytest
from fastapi.testclient import TestClient
import hub.app as module
from hub.store import Store
from hub.engine import Engine

@pytest.fixture
def client(tmp_path,monkeypatch):
    store=Store(tmp_path/'api.sqlite3')
    engine=Engine(store)
    monkeypatch.setattr(module,'store',store)
    monkeypatch.setattr(module,'engine',engine)
    monkeypatch.setattr(module,'STATE',tmp_path)
    monkeypatch.setattr(engine,'enqueue',lambda task_id:None)
    with TestClient(module.app) as c:
        yield c

def test_auth_and_csrf(client):
    assert client.get('/api/tasks').status_code==401
    assert client.get('/').status_code==200
    assert client.get('/api/tasks').status_code==200
    assert client.post('/api/stop',json={}).status_code==403
    assert client.post('/api/stop',json={},headers={'origin':'https://evil.example'}).status_code==403
    assert client.post('/api/stop',json={},headers={'origin':'http://127.0.0.1:8876'}).status_code==200


def test_connector_catalog_mcp_and_ui_share_availability_without_claiming_login(client,monkeypatch):
    import asyncio
    from hub import mcp_gateway as gateway
    async def local(path,data=None):
        return client.get(path,headers={'x-hub-key':module.TOKEN}).json()
    monkeypatch.setattr(gateway,'local',local)
    result=asyncio.run(gateway.ai_connector_catalog())
    assert result==client.get('/api/ai-connectors',headers={'x-hub-key':module.TOKEN}).json()
    providers={item['id']:item for item in result['items']}
    assert providers['chatgpt']['connection_state']=='not_checked'
    assert {t['id'] for t in providers['chatgpt']['transports']}=={'play','mcp'}
    for provider in ('claude','deepseek'):
        assert providers[provider]['connection_state']=='not_implemented'
        assert not any(t['implemented'] for t in providers[provider]['transports'])

def test_connection_mcp_http_and_active_handoff_guard(client,tmp_path,monkeypatch):
    import asyncio
    from hub import mcp_gateway as gateway
    chats=module.conversations();chat=chats.create(chats.project(str(tmp_path))['id'])['id']
    headers={'x-hub-key':module.TOKEN}
    async def local(path,data=None):
        response=client.get(path,headers=headers) if data is None else client.post(path,json=data,headers=headers)
        assert response.status_code==200,response.text
        return response.json()
    monkeypatch.setattr(gateway,'local',local)
    saved=asyncio.run(gateway.chatgpt_conversation_connection(chat,'mcp',True,'https://chatgpt.com/c/example'))
    assert saved['connected'] is False
    assert asyncio.run(gateway.chatgpt_favorite_conversations())['items'][0]['chat_id']==chat
    assert client.post('/api/chatgpt/context',json={'chat_id':chat},headers=headers).json()['transport']=='mcp'
    controller=module.app.state.bridge
    controller.state.update(chat_id=chat,enabled=True,phase='waiting_task')
    assert client.post(f'/api/chats/{chat}/connection',json={'transport':'play'},headers=headers).status_code==409
    assert client.post(f'/api/chats/{chat}/connection',json={'favorite':False},headers=headers).status_code==200
    controller.state.update(enabled=False,phase='stopped')
    assert client.post(f'/api/chats/{chat}/connection',json={'transport':'play'},headers=headers).status_code==200
    assert controller.state['chat_id'] is None

def test_new_play_bootstraps_same_new_local_chat_and_cannot_duplicate_while_active(client,tmp_path,monkeypatch):
    project=module.conversations().project(str(tmp_path))['id']
    controller=module.app.state.bridge;bridge=controller.bridge;sent=[];opened=[]
    async def open_conversation(url=None):
        opened.append(url);bridge.bound_url='https://chatgpt.com/c/new-play-test';return {'ready':True}
    async def connect():return {'ready':True}
    async def read():return {'url':bridge.bound_url,'title':'New PLAY','users':[],'user_messages':[]}
    async def send(text):sent.append(text)
    monkeypatch.setattr(bridge,'open_conversation',open_conversation)
    monkeypatch.setattr(bridge,'connect',connect)
    monkeypatch.setattr(bridge,'read',read)
    monkeypatch.setattr(bridge,'send',send)
    headers={'x-hub-key':module.TOKEN}
    result=client.post('/api/chatgpt/new-conversation',json={'project_id':project},headers=headers)
    assert result.status_code==200,result.text
    chat=result.json()['chat_id']
    assert opened==[None] and len(sent)==1 and chat in sent[0] and 'PLAY OPERATING CONTRACT' in sent[0]
    assert controller.transcript.remote(chat)==bridge.bound_url
    assert result.json()['play_bootstrap']=='sent_not_yet_verified_by_remote_reply'
    assert client.post('/api/chatgpt/new-conversation',json={'project_id':project},headers=headers).status_code==409
    assert len(sent)==1
    controller.stop()


def test_connection_probe_survives_polling_without_erasing_uncertain_send(client,monkeypatch):
    controller=module.app.state.bridge
    controller.state.update(enabled=False,phase='send_uncertain',pending_outbound_text='keep evidence')
    async def probe(tab_id=None,create=False):
        return {'connected':True,'ready':False,'login_required':True,'reason':'Sign in required'}
    monkeypatch.setattr(module.engine.runner.chatgpt,'connect',probe)
    headers={'x-hub-key':module.TOKEN}
    assert client.post('/api/chatgpt/connect',json={},headers=headers).status_code==200
    status=client.get('/api/chatgpt/status',headers=headers).json()
    assert status['last_connection_check']['login_required'] and status['last_connection_check']['checked_at']
    assert status['phase']=='send_uncertain' and status['pending_outbound_text']=='keep evidence'

def test_play_setup_failure_is_visible_and_retained(client,tmp_path,monkeypatch):
    project=module.conversations().project(str(tmp_path))['id']
    controller=module.app.state.bridge
    async def fail(chat_id):
        assert controller.state['phase']=='opening_conversation'
        raise TimeoutError()
    monkeypatch.setattr(controller,'select_context',fail)
    response=client.post('/api/chatgpt/new-conversation',json={'project_id':project},headers={'x-hub-key':module.TOKEN})
    assert response.status_code==409
    assert 'timed out' in response.json()['detail']
    assert controller.state['phase']=='connection_attention' and controller.state['enabled'] is False
    messages=controller.transcript.list(controller.state['play_setup_chat_id'])
    assert messages[-1]['status']=='needs_review' and 'timed out' in messages[-1]['text']


def test_memory_feedback_mcp_and_http_share_persisted_evidence(client,tmp_path,monkeypatch):
    import asyncio
    from hub import mcp_gateway as gateway
    chats=module.conversations()
    chat=chats.create(chats.project(str(tmp_path))['id'])['id']
    source=chats.submit(chat,'Remember project Cedar','inspect','feedback-source')['id']
    module.store.update(source,state='done',result='Project name: Cedar')
    headers={'x-hub-key':module.TOKEN}
    async def local(path,data=None):
        response=client.get(path,headers=headers) if data is None else client.post(path,json=data,headers=headers)
        assert response.status_code==200,response.text
        return response.json()
    monkeypatch.setattr(gateway,'local',local)
    saved=asyncio.run(gateway.conversation_memory_feedback_settings(chat,True,'mcp'))
    assert saved['enabled'] and saved['transport']=='mcp'
    assert client.get(f'/api/chats/{chat}/memory-review/settings',headers=headers).json()['enabled']
    packet=asyncio.run(gateway.conversation_memory_review_request(chat,source,'Is the project Cedar?','Cedar'))
    assert packet['request']['excerpt']=='Project name: Cedar'
    reply=asyncio.run(gateway.conversation_memory_review_reply(chat,packet['id'],'confirmed',False,'Original chat is not available'))
    assert reply['response']['verdict']=='unavailable'
    assert asyncio.run(gateway.conversation_memory_review_status(chat,packet['id']))['status']=='reviewed'
    assert module.store.get(source)['result']=='Project name: Cedar'

def test_resume_handoff_preserves_identity_and_rejects_unresolved_send(client,tmp_path):
    headers={'x-hub-key':module.TOKEN}
    task=module.store.create('Resume original work',str(tmp_path),'desktop','resume-handoff')
    task=module.store.update(task['id'],state='waiting_user')
    bridge=module.app.state.bridge
    bridge.state.update(task_id=task['id'],chat_id='linked-chat',enabled=False,phase='stopped',pending_outbound_text='unsent')
    body={'command':'resume','expected_revision':task['revision'],'resume_handoff':True}
    url=f"/api/tasks/{task['id']}/control"
    assert client.post(url,json=body,headers=headers).status_code==409
    assert module.store.get(task['id'])['state']=='waiting_user'
    bridge.state['pending_outbound_text']=None
    result=client.post(url,json=body,headers=headers)
    assert result.status_code==200
    assert result.json()['id']==task['id'] and bridge.state['task_id']==task['id']
    assert bridge.state['enabled'] and bridge.state['phase']=='waiting_task'
    bridge.state['enabled']=False

def test_dns_rebinding(client):
    assert client.get('/',headers={'host':'attacker.example:8876'}).status_code==403

def test_binary_upload_download_and_incomplete_limit(client,tmp_path,monkeypatch):
    from hub.file_library import FileLibrary,MAX_UPLOAD
    library=FileLibrary(tmp_path/'library-state',tmp_path/'files')
    monkeypatch.setattr(module,'file_library',lambda:library)
    raw=b'RIFF'+b'\x00\xff'*1_100_000
    headers={'x-hub-key':module.TOKEN,'content-type':'audio/wav'}
    result=client.post('/api/files/upload?name=voice.wav',content=raw,headers=headers)
    assert result.status_code==200,result.text
    item=result.json();assert item['status']=='ready' and item['size']==len(raw)
    response=client.get('/api/files/'+item['id']+'/content',headers=headers)
    assert response.content==raw and 'attachment;' in response.headers['content-disposition']
    assert client.post('/api/files/upload?name=large.wav',content=b'x',headers={**headers,'content-length':str(MAX_UPLOAD+1)}).status_code==413
    assert client.get('/api/files/nonexistent/content',headers=headers).status_code==404
    assert 'data:' in client.get('/').headers['content-security-policy']

def test_task_idempotency(client,tmp_path):
    headers={'x-hub-key':module.TOKEN}
    body={'goal':'test','workspace':str(tmp_path),'mode':'inspect','idempotency_key':'request-123'}
    first=client.post('/api/tasks',json=body,headers=headers)
    second=client.post('/api/tasks',json=body,headers=headers)
    assert first.status_code==201
    assert first.json()['id']==second.json()['id']
    body['goal']='changed'
    assert client.post('/api/tasks',json=body,headers=headers).status_code==409

def test_stale_review_and_failed_evidence(client,tmp_path):
    headers={'x-hub-key':module.TOKEN}
    t=module.store.create('test',str(tmp_path),'code','unique-123',[{'path':'missing.txt'}])
    module.store.update(t['id'],state='waiting_review')
    path=f"/api/tasks/{t['id']}/review"
    assert client.post(path,json={'decision':'approve','reason':'checked','expected_revision':1},headers=headers).status_code==409
    assert client.post(path,json={'decision':'approve','reason':'checked','expected_revision':2},headers=headers).status_code==409

def test_artifact_cannot_escape(client,tmp_path):
    headers={'x-hub-key':module.TOKEN}
    t=module.store.create('test',str(tmp_path),'code','unique-124')
    assert client.get(f"/api/tasks/{t['id']}/artifacts/..%5Chub.key",headers=headers).status_code==404

def test_changed_evidence_rejects_approval(client,tmp_path):
    headers={'x-hub-key':module.TOKEN}
    proof=tmp_path/'proof.txt'
    proof.write_text('version one')
    t=module.store.create('test',str(tmp_path),'code','unique-125',[{'path':'proof.txt'}])
    module.store.event(t['id'],'verification',{'checks':module.engine.verify(t),'evidence':[]})
    t=module.store.update(t['id'],state='waiting_review')
    proof.write_text('version two')
    r=client.post(f"/api/tasks/{t['id']}/review",json={'decision':'approve','reason':'checked','expected_revision':t['revision']},headers=headers)
    assert r.status_code==409

def test_session_transfer_requires_one_time_code(client,monkeypatch):
    async def fake_import(data):
        return {'imported_cookies':len(data['cookies']),'login_verified':False}
    monkeypatch.setattr(module.engine.runner.browser,'import_session',fake_import)
    payload={'url':'https://example.com','cookies':[],'code':'wrong'}
    assert client.post('/bridge/import',json=payload).status_code==400
    pair=client.post('/api/browser/pair',json={},headers={'x-hub-key':module.TOKEN})
    assert pair.status_code==200
    payload['code']=pair.json()['code']
    assert client.post('/bridge/import',json=payload).status_code==200
    assert client.post('/bridge/import',json=payload).status_code==400

def test_mobile_pairing_requires_code(client):
    remote=TestClient(module.app,client=('10.0.0.55',1234),base_url='http://100.78.233.10:8876')
    assert remote.get('/').status_code==401
    assert remote.get('/api/tasks').status_code==401
    paired=client.post('/api/mobile/pair',headers={'x-hub-key':module.TOKEN}).json()
    assert remote.get(paired['url']).status_code==200
    assert remote.get('/api/tasks').status_code==200
    assert remote.get(paired['url']).status_code==400

def test_project_files_confined_and_notes(client,tmp_path):
    headers={'x-hub-key':module.TOKEN}
    (tmp_path/'note.txt').write_text('preview proof')
    p=client.post('/api/projects',json={'path':str(tmp_path)},headers=headers).json()
    r=client.get('/api/projects/'+p['id']+'/files?path=note.txt',headers=headers)
    assert r.json()['content']=='preview proof'
    assert client.get('/api/projects/'+p['id']+'/files?path=../outside',headers=headers).status_code==400
    assert client.post('/api/projects/'+p['id']+'/notes',json={'notes':'Use Hebrew'},headers=headers).status_code==200
    assert client.get('/api/projects/'+p['id']+'/notes',headers=headers).json()['notes']=='Use Hebrew'

def test_worktree_creates_isolated_project(client,tmp_path,monkeypatch):
    import subprocess
    repo=tmp_path/'repo';repo.mkdir()
    subprocess.run(['git','init',str(repo)],check=True,capture_output=True)
    (repo/'a.txt').write_text('original')
    subprocess.run(['git','-C',str(repo),'add','a.txt'],check=True,capture_output=True)
    subprocess.run(['git','-C',str(repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture'],check=True,capture_output=True)
    monkeypatch.setattr(module,'ROOT',tmp_path/'root')
    headers={'x-hub-key':module.TOKEN}
    project=client.post('/api/projects',json={'path':str(repo)},headers=headers).json()
    response=client.post('/api/worktrees',json={'project_id':project['id']},headers=headers)
    assert response.status_code==200,response.text
    from pathlib import Path
    copied=Path(response.json()['path'])/'a.txt'
    assert copied.read_text()=='original'
    copied.write_text('isolated')
    assert (repo/'a.txt').read_text()=='original'
