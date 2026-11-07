import asyncio
import base64
import hashlib
from urllib.parse import urlsplit, parse_qs

import pytest
from fastapi.testclient import TestClient
from hub import mcp_auth as auth, mcp_gateway as gateway
from hub.file_library import FileLibrary
from hub.relay import command


@pytest.fixture
def remote(tmp_path, monkeypatch):
    import importlib
    importlib.reload(gateway)
    monkeypatch.setattr(auth, 'HOME', tmp_path/'oauth')
    monkeypatch.setattr(gateway, 'HOME', tmp_path/'oauth')
    with TestClient(gateway.app, base_url=gateway.PUBLIC) as client:
        yield client


def authorize(client):
    result=client.post('/register', json={'client_name':'Regression client', 'redirect_uris':['https://chatgpt.com/connector/oauth/callback'], 'token_endpoint_auth_method':'none', 'grant_types':['authorization_code','refresh_token'], 'response_types':['code'], 'scope':'agent'})
    assert result.status_code==201, result.text
    registration=result.json()
    verifier='test-verifier-'+'a'*50
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    response=client.get('/authorize', params={'client_id':registration['client_id'],'redirect_uri':registration['redirect_uris'][0],'response_type':'code','scope':'agent','state':'test-state','code_challenge':challenge,'code_challenge_method':'S256','resource':gateway.PUBLIC+'/mcp'},follow_redirects=False)
    assert response.status_code==302, response.text
    ticket=parse_qs(urlsplit(response.headers['location']).query)['ticket'][0]
    assert client.get('/consent',params={'ticket':ticket}).status_code==200
    auth.approve(auth.digest(ticket), True)
    approved=client.get('/consent',params={'ticket':ticket},follow_redirects=False)
    query=parse_qs(urlsplit(approved.headers['location']).query)
    assert query['state']==['test-state']
    return {'grant_type':'authorization_code','client_id':registration['client_id'],'redirect_uri':registration['redirect_uris'][0], 'code':query['code'][0],'code_verifier':verifier,'resource':gateway.PUBLIC+'/mcp'}


def test_oauth_pkce_replay_revocation_and_mcp(remote):
    assert remote.post('/mcp',json={}).status_code==401
    data=authorize(remote)
    assert remote.post('/token',data={**data,'code_verifier':'wrong'}).status_code==400
    token=remote.post('/token',data=data)
    assert token.status_code==200,token.text
    assert remote.post('/token',data=data).status_code==400
    tokens=token.json()
    headers={'Authorization':'Bearer '+tokens['access_token'], 'Accept':'application/json, text/event-stream'}
    result=remote.post('/mcp',headers=headers,json={'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}})
    assert result.status_code==200,result.text
    assert 'submit_task' in [t['name'] for t in result.json()['result']['tools']]
    refreshed=remote.post('/token',data={'grant_type':'refresh_token','client_id':data['client_id'],'refresh_token':tokens['refresh_token'],'scope':'agent','resource':gateway.PUBLIC+'/mcp'})
    assert refreshed.status_code==200,refreshed.text
    assert remote.post('/token',data={'grant_type':'refresh_token','client_id':data['client_id'],'refresh_token':tokens['refresh_token'],'scope':'agent'}).status_code==400
    # Revoking the grant invalidates both old access and rotated tokens.
    with auth.db() as conn:conn.execute("DELETE FROM records WHERE kind='grant'")
    assert remote.post('/mcp',headers=headers,json={}).status_code==401
    assert asyncio.run(auth.provider.load_access_token(refreshed.json()['access_token'])) is None


def test_reject_redirect_and_resource(remote):
    for uri in ['http://chatgpt.com/callback','https://chatgpt.com.evil.example/callback','https://evil.example/callback']:
        result=remote.post('/register',json={'redirect_uris':[uri],'token_endpoint_auth_method':'none'})
        assert result.status_code==400
    assert remote.get('/files/'+'a'*32,params={'expires':1,'signature':'bad'}).status_code==403


def test_file_receipt_and_expiry(remote,tmp_path,monkeypatch):
    library=FileLibrary(tmp_path/'state',tmp_path/'files')
    monkeypatch.setattr(gateway,'FileLibrary',lambda:library)
    raw=b'%PDF-1.7\nknown bytes\n%%EOF'
    item=library.import_bytes('report.pdf',raw,'application/pdf')
    result=asyncio.run(gateway.get_file(item['id']))
    import json
    record=json.loads(result.content[0].text)
    response=remote.get(record['download_url'])
    assert response.status_code==200 and response.content==raw
    assert hashlib.sha256(response.content).hexdigest()==record['sha256']
    assert remote.get(record['download_url'].replace(item['id'],'b'*32)).status_code==403


def test_submission_uses_existing_runner_and_stable_identity(monkeypatch):
    calls=[]
    async def local(path,data=None):calls.append((path,data));return {'id':'task'}
    monkeypatch.setattr(gateway,'local',local)
    async def wait(task_id):return {'id':task_id}
    monkeypatch.setattr(gateway,'wait_for_task',wait)
    for _ in range(2):asyncio.run(gateway.submit_task('a'*32,'Inspect current state','stable-request-1','inspect'))
    assert calls[0]==calls[1]
    assert calls[0][0]=='/api/chats/'+'a'*32+'/messages'
    assert calls[0][1]['request_id']=='stable-request-1'
    with pytest.raises(ValueError):asyncio.run(gateway.submit_task('../escape','test','stable-request-1'))


def test_tunnel_is_loopback_pinned_and_noninteractive():
    args=command({'known_hosts':'E:/state/known_hosts','identity_file':'E:/state/key','relay_port':18897,'relay_user':'local-agent-tunnel','relay_host':'example.test'})
    assert 'StrictHostKeyChecking=yes' in args
    assert 'BatchMode=yes' in args
    assert args[args.index('-R')+1]=='127.0.0.1:18897:127.0.0.1:8897'
    assert args[-1]=='local-agent-tunnel@example.test'
