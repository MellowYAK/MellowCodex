"""The local LLM must navigate and submit the fixture using real browser tools."""
import asyncio,json,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from browser_acceptance import Handler,ThreadingHTTPServer
import httpx
from hub.config import STATE,ARTIFACTS
from hub.session import session_status

async def main(url):
    session_before=session_status()
    headers={'X-Hub-Key':(STATE/'hub.key').read_text().strip()}
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8876',headers=headers,timeout=20,trust_env=False) as client:
        body={'goal':f'Use the built-in browser to open {url}. Fill the Message field with the string "LOCAL_AGENT_BROWSER_OK" (without quotation marks or any extra words). Click Save message. Verify the page says Saved: LOCAL_AGENT_BROWSER_OK. Use only browser tools, do not write any files or run shell. Finish with the observed result.','workspace':'E:/AI/repos/sandbox','mode':'browser','idempotency_key':'browser-live-'+str(time.time_ns()),'criteria':[]}
        r=await client.post('/api/tasks',json=body);r.raise_for_status();task=r.json();started=time.monotonic();last=0
        while time.monotonic()-started<240:
            task=(await client.get('/api/tasks/'+task['id'])).json()
            if task['state'] in ('done','waiting_review','failed','waiting_user','cancelled'):break
            if time.monotonic()-started-last>20:
                last=time.monotonic()-started;print(json.dumps({'elapsed_seconds':round(last,1),'state':task['state']}),flush=True)
            await asyncio.sleep(2)
        bundle=(await client.get('/api/tasks/'+task['id']+'/review')).json()
        actions=bundle['actions'];tools=[a['tool'] for a in actions]
        observed=any('Saved: LOCAL_AGENT_BROWSER_OK' in json.dumps(a.get('result')) for a in actions if a['tool']=='browser_act')
        report={'session_before':session_before,'session_after':session_status(),'task_id':task['id'],'elapsed_seconds':round(time.monotonic()-started,2),'state':task['state'],'tools':tools,'verified_page_result':observed,'result':task['result']}
        (ARTIFACTS/('agent-browser-'+task['id']+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=True,indent=2),flush=True)
        if not observed:raise RuntimeError('The model did not verify the expected browser result')

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    try:asyncio.run(main(f'http://127.0.0.1:{server.server_port}/'))
    finally:server.shutdown()
