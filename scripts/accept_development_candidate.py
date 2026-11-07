"""Opt-in real Ollama/Engine acceptance, isolated state; never a fixture pass claim.

Run from repository root with LOCAL_AGENT_ROOT pointing at a dedicated evidence
directory. Refuses the production root and a busy Ollama instance. Uses the
installed model, does not download one. Unloads only its own model on exit.
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')

async def main():
    chosen=os.environ.get('LOCAL_AGENT_ROOT','')
    if not chosen or Path(chosen).resolve()==Path('E:/AI').resolve():raise RuntimeError('Set a dedicated LOCAL_AGENT_ROOT')
    from hub.config import ROOT,STATE,OLLAMA
    from hub.store import Store
    from hub.conversations import Conversations
    from hub.model_settings import ModelSettings,save_settings
    from hub.context import ProjectContext
    from hub.engine import Engine
    model=os.environ.get('ACCEPTANCE_MODEL','qwen3.5:4b')
    async with httpx.AsyncClient(timeout=30,trust_env=False) as client:
        state=(await client.get(OLLAMA+'/api/ps')).json()
        if state.get('models'):raise RuntimeError('Ollama busy: do not disrupt existing work')
    save_settings(ModelSettings(model=model,context_tokens=16384,response_tokens=1024,request_timeout_seconds=300,visual_guidance=False,keep_alive_minutes=2))
    root=ROOT/'fixture';root.mkdir(exist_ok=True)
    (root/'billing.py').write_text('import decimal\n\ndef calculate_total(price, quantity):\n    return price + quantity\n',encoding='utf-8')
    (root/'test_billing.py').write_text('from billing import calculate_total\n\ndef test_total():\n    assert calculate_total(7, 4) == 28\n',encoding='utf-8')
    store=Store(STATE/'hub.sqlite3');conversations=Conversations(store)
    p=conversations.project(str(root));svc=ProjectContext(STATE,conversations)
    svc.annotate(p['id'],'billing.py',['חישוב חשבון','расчёт счёта'],['billing'],must_not_break=['Keep calculate_total(price, quantity) signature.'])
    chat=conversations.create(p['id'])
    worker_mode=os.environ.get('ACCEPTANCE_WORKER')=='1'
    goal=('Fix calculate_total(price, quantity) in billing.py to multiply price by quantity. Preserve test_billing.py unchanged. Use candidate_create then candidate_repair with paths=["billing.py"], tests=["test_billing.py"], model="qwen2.5-coder:7b" and the returned candidate revision. The worker will propose and test the change. Inspect its test and diff evidence, then call candidate_diff. Do not edit live files, run shell commands or activate changes.' if worker_mode else 'Fix billing.py only in an isolated candidate, never edit the live workspace. First use candidate_create, inspect its returned file hashes, then candidate_patch at the exact revision to make calculate_total return price * quantity. Preserve test_billing.py unchanged. Run candidate_test for test_billing.py at the resulting revision, and report the verified outcome and candidate id. Do not run tests using run_shell or write_file; use candidate tools for this request.')
    task=conversations.submit(chat['id'],goal,
       'code','candidate-real-'+str(time.time_ns()))
    from hub.development.guidance import Guidance
    guide=Guidance(store)
    guide.submit(task['id'],task['revision'],0,'','acceptance-guidance',('You must delegate the scoped source repair to candidate_repair using qwen2.5-coder:7b; direct candidate_patch is not the requested worker test. ' if worker_mode else '')+'After the candidate test, call candidate_diff and include the exact changed path in your response. Do not activate the candidate.',required_tools=['candidate_repair','candidate_diff'] if worker_mode else ['candidate_diff'])
    engine=Engine(store);started=time.monotonic()
    try:
        await asyncio.wait_for(engine.run(task['id']),timeout=720)
        final=store.get(task['id']);actions=store.actions(task['id'])
        names=[a['tool'] for a in actions if a['state']=='complete' and not (a.get('result') or {}).get('error')]
        evidence={'task_id':task['id'],'model':model,'elapsed_seconds':round(time.monotonic()-started,2),'state':final['state'],'result':final['result'],'tools':names,'actions':actions,'guidance':guide.status(task['id']),'guidance_events':[e for e in store.events(task['id']) if e['kind'].startswith('guidance_')],
                  'required_candidate_tools_used':all(n in names for n in (['candidate_create','candidate_repair','candidate_diff'] if worker_mode else ['candidate_create','candidate_patch','candidate_test','candidate_diff'])),
                  'live_source_preserved':(root/'billing.py').read_text(encoding='utf-8')=='import decimal\n\ndef calculate_total(price, quantity):\n    return price + quantity\n','test_preserved':(root/'test_billing.py').read_text(encoding='utf-8')=='from billing import calculate_total\n\ndef test_total():\n    assert calculate_total(7, 4) == 28\n'}
        (ROOT/'acceptance.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in evidence.items() if k not in ('actions','code','guidance','guidance_events')},ensure_ascii=False))
    finally:
        async with httpx.AsyncClient(timeout=60,trust_env=False) as client:
            response=await client.post(OLLAMA+'/api/generate',json={'model':model,'keep_alive':0});response.raise_for_status()
            if worker_mode:
                response=await client.post(OLLAMA+'/api/generate',json={'model':'qwen2.5-coder:7b','keep_alive':0});response.raise_for_status()
            print(json.dumps({'remaining_models':(await client.get(OLLAMA+'/api/ps')).json().get('models',[])}))

if __name__=='__main__':asyncio.run(main())
