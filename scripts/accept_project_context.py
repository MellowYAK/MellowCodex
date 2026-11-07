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
    model='qwen3.5:4b'
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
    task=conversations.submit(chat['id'],
       'תקן את חישוב החשבון בפרויקט. מחיר כפול כמות הוא הסכום הנכון. השתמש ב-context_search לחיפוש, ב-context_expand לקריאת המקור וב-context_related כדי לזהות את קובץ הבדיקה לפני שינוי. הרץ את הבדיקה הקיימת באמצעות E:/AI/tools/hub-venv/Scripts/python.exe -m pytest test_billing.py -q וודא שעברה. אל תשנה את הבדיקה.',
       'code','context-real-'+str(time.time_ns()))
    engine=Engine(store);started=time.monotonic()
    try:
        await asyncio.wait_for(engine.run(task['id']),timeout=720)
        final=store.get(task['id']);actions=store.actions(task['id'])
        names=[a['tool'] for a in actions if a['state']=='complete' and not (a.get('result') or {}).get('error')]
        evidence={'task_id':task['id'],'model':model,'elapsed_seconds':round(time.monotonic()-started,2),'state':final['state'],'result':final['result'],'tools':names,'actions':actions,
                  'required_context_used':all(n in names for n in ['context_search','context_expand','context_related']),
                  'code':(root/'billing.py').read_text(encoding='utf-8'),'test_preserved':(root/'test_billing.py').read_text(encoding='utf-8')=='from billing import calculate_total\n\ndef test_total():\n    assert calculate_total(7, 4) == 28\n'}
        (ROOT/'acceptance.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in evidence.items() if k not in ('actions','code')},ensure_ascii=False))
    finally:
        async with httpx.AsyncClient(timeout=60,trust_env=False) as client:
            response=await client.post(OLLAMA+'/api/generate',json={'model':model,'keep_alive':0});response.raise_for_status()
            print(json.dumps({'remaining_models':(await client.get(OLLAMA+'/api/ps')).json().get('models',[])}))

if __name__=='__main__':asyncio.run(main())
