"""Explicit live acceptance: OAuth -> public tunnel -> agent-owned inspect task.

Creates a named test conversation and revokes only this test's OAuth grant.
Never prints or writes access/refresh tokens or the Hub key.
"""
import base64,hashlib,json,secrets,sys,time
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from hub.config import STATE,PORT,ARTIFACTS
from hub.remote_config import PUBLIC


def main():
    screenshot='--screenshot' in sys.argv
    key=(STATE/'hub.key').read_text().strip()
    tokens=None;registration=None;report={};seq=0
    with httpx.Client(base_url=PUBLIC,timeout=25) as public, httpx.Client(base_url=f'http://127.0.0.1:{PORT}',headers={'x-hub-key':key},timeout=15) as local:
        try:
            report['unauthenticated_status']=public.post('/mcp',json={}).status_code
            assert report['unauthenticated_status']==401
            response=public.post('/register',json={'client_name':'Local Agent bridge acceptance','redirect_uris':['https://chatgpt.com/connector/oauth/callback'],'token_endpoint_auth_method':'client_secret_post','grant_types':['authorization_code','refresh_token'],'response_types':['code'],'scope':'agent'})
            response.raise_for_status();registration=response.json()
            verifier=secrets.token_urlsafe(48)
            challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
            response=public.get('/authorize',params={'client_id':registration['client_id'],'redirect_uri':registration['redirect_uris'][0],'response_type':'code','scope':'agent','state':'acceptance','code_challenge':challenge,'code_challenge_method':'S256','resource':PUBLIC+'/mcp'},follow_redirects=False)
            ticket=parse_qs(urlsplit(response.headers['location']).query)['ticket'][0]
            digest=hashlib.sha256(ticket.encode()).hexdigest()
            response=local.post('/api/remote/approve',json={'request_id':digest,'allow':True});response.raise_for_status()
            response=public.get('/consent',params={'ticket':ticket},follow_redirects=False)
            code=parse_qs(urlsplit(response.headers['location']).query)['code'][0]
            response=public.post('/token',data={'grant_type':'authorization_code','client_id':registration['client_id'],'client_secret':registration['client_secret'],'redirect_uri':registration['redirect_uris'][0],'code':code,'code_verifier':verifier,'resource':PUBLIC+'/mcp'})
            response.raise_for_status();tokens=response.json()
            public.headers.update({'Authorization':'Bearer '+tokens['access_token'],'Accept':'application/json, text/event-stream'})
            def rpc(method,params):
                nonlocal seq
                seq+=1;response=public.post('/mcp',json={'jsonrpc':'2.0','id':seq,'method':method,'params':params});response.raise_for_status()
                body=response.json()
                if 'error' in body:raise RuntimeError(str(body['error']))
                return body['result']
            def tool(name,arguments):
                result=rpc('tools/call',{'name':name,'arguments':arguments})
                if result.get('isError'):raise RuntimeError(str(result['content']))
                return result.get('structuredContent') or json.loads(result['content'][0]['text'])
            initialized=rpc('initialize',{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'relay-acceptance','version':'1'}})
            report['protocol']=initialized['protocolVersion']
            report['tools']=[t['name'] for t in rpc('tools/list',{})['tools']]
            inventory=tool('list_projects_and_chats',{})
            project=next(p for p in inventory['projects'] if Path(p['path']).name=='sandbox')
            chat=tool('create_chat',{'project_id':project['id']})
            args={'chat_id':chat['id'],'request':'Bridge acceptance: use list_files to list the immediate contents of the current project root. Report observed file names. Read-only; do not edit anything or consult ChatGPT.','request_id':'mcp-acceptance-'+secrets.token_hex(12),'mode':'inspect'}
            if screenshot:args.update(request='Take a current screenshot of the Windows desktop and return its original PNG file ID. Do not change anything else.',mode='desktop')
            start=time.monotonic();task=tool('submit_task',args)
            report.update(task_id=task['id'],chat_id=chat['id'],submission_seconds=round(time.monotonic()-start,3))
            assert tool('submit_task',args)['id']==task['id']
            report['duplicate_submission_same_task']=True
            print(json.dumps({'accepted':task['id'],'seconds':report['submission_seconds']}),flush=True)
            while time.monotonic()-start<240:
                status=tool('get_task',{'task_id':task['id']});task=status['task']
                if task['state'] not in ('queued','running','verifying','waiting_desktop'):break
                print(json.dumps({'state':task['state'],'elapsed':round(time.monotonic()-start,1)}),flush=True)
                time.sleep(4)
            report.update(elapsed_seconds=round(time.monotonic()-start,2),state=task['state'],result=task['result'],actions=status['recent_actions'])
            assert any(a['tool']==('capture_screenshot' if screenshot else 'list_files') and a['state']=='complete' for a in status['recent_actions']), status['recent_actions']
            assert task['state'] in ('waiting_review','done'),task['state']
            saved=tool('get_chat',{'chat_id':chat['id']})
            assert sum(t['id']==task['id'] for t in saved['turns'])==1
            report['saved_once']=True
            from hub.file_library import FileLibrary
            raw='Bridge file receipt: שלום'.encode('utf-8')
            if screenshot:
                capture=next(a for a in status['recent_actions'] if a['tool']=='capture_screenshot')
                evidence=json.loads(capture['result']) if isinstance(capture['result'],str) else capture['result']
                item=FileLibrary().get(evidence['id'],ready=True);raw=Path(item['path']).read_bytes()
            else:item=FileLibrary().import_bytes('bridge-acceptance.txt',raw,'text/plain','developer MCP acceptance fixture')
            delivery=tool('get_file',{'file_id':item['id']})
            downloaded=public.get(delivery['download_url']);downloaded.raise_for_status()
            assert downloaded.content==raw
            report['file_download_sha256']=hashlib.sha256(downloaded.content).hexdigest()
            report['file_delivery_verified']=True
        finally:
            if tokens:
                response=public.post('/revoke',data={'token':tokens['refresh_token'],'token_type_hint':'refresh_token','client_id':registration['client_id'],'client_secret':registration['client_secret']})
                report['revocation_status']=response.status_code
                report['revoked_access_status']=public.post('/mcp',json={}).status_code
            ARTIFACTS.mkdir(parents=True,exist_ok=True)
            (ARTIFACTS/('mcp-screenshot-acceptance.json' if screenshot else 'mcp-acceptance.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report,ensure_ascii=True),flush=True)


if __name__=='__main__':main()
