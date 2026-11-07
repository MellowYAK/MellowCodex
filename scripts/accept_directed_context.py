"""Run a recorded director step through the real Engine in isolated state.

No server restart or desktop automation. Input is a JSON object containing
request and objective, supplied by an authorized feedback conversation.
"""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',required=True)
    parser.add_argument('--step',required=True)
    parser.add_argument('--autonomous',action='store_true',help='Run the user request without director events, guidance, supplied source ranges or GPT feedback')
    parser.add_argument('--resume-task',help='Apply a recorded director correction to an existing waiting_review task in this isolated store')
    args=parser.parse_args()
    chosen=os.environ.get('LOCAL_AGENT_ROOT','')
    if not chosen or Path(chosen).resolve()==Path('E:/AI').resolve():
        raise RuntimeError('A dedicated acceptance root is required')
    from hub.config import ROOT,STATE
    from hub.store import Store
    from hub.conversations import Conversations
    from hub.context import ProjectContext
    from hub.context.indexing import Indexing
    from hub.model_settings import ModelSettings,save_settings
    from hub.engine import Engine
    step=json.loads(Path(args.step).read_text(encoding='utf-8-sig'))
    if args.autonomous and (args.resume_task or step.get('required_sources') or 'allowed_tools' in step or step.get('context_read')):
        raise ValueError('Autonomous acceptance cannot inject director constraints or resume a directed task')
    store=Store(STATE/'hub.sqlite3');conversations=Conversations(store)
    project=conversations.project(args.project)
    svc=ProjectContext(STATE,conversations);queue=Indexing(svc)
    queue.settings(project['id'],False,'fast')
    queue.selected(project['id']).refresh(project['id'])
    save_settings(ModelSettings(model='qwen3.5:4b',context_tokens=16384,response_tokens=1600,
                                request_timeout_seconds=180,visual_guidance=False,keep_alive_minutes=2))
    if args.resume_task:
        task=store.get(args.resume_task)
        if task['state']!='waiting_review' or Path(task['workspace']).resolve()!=Path(args.project).resolve():
            raise RuntimeError('Correction requires the same project and an observed waiting_review task')
        if any(a['state']=='pending' for a in store.actions(task['id'])):
            raise RuntimeError('Uncertain actions must be reconciled before correction')
    else:
        chat=conversations.create(project['id'],'Autonomous source acceptance' if args.autonomous else 'Directed source acceptance')
        goal=step['request'] if args.autonomous else 'CURRENT STEP — execute only this step:\n'+step['request']+'\n\nOVERALL HUMAN OBJECTIVE — scope only:\n'+step['objective']
        task=conversations.submit(chat['id'],goal,'code','directed-'+str(time.time_ns()))
    if not args.autonomous:
        store.event(task['id'],'chatgpt_action',{'action_id':step.get('id','acceptance'),'request':step['request']})
    if args.resume_task or step.get('required_sources') or 'allowed_tools' in step or step.get('context_read'):
        from hub.development.guidance import Guidance
        guide=Guidance(store);status=guide.status(task['id'])
        guide.submit(task['id'],task['revision'],status['guidance_revision'],status['consumer_epoch'],step.get('id','source-step'),
                     step['request'],required_sources=step.get('required_sources'),allowed_tools=step.get('allowed_tools'),evidence_only=step.get('evidence_only',False),context_read=step.get('context_read'))
    if args.resume_task:
        messages=task['messages']+[{'role':'user','content':step['request']}]
        task=store.update(task['id'],expected=task['revision'],kind='review',state='queued',messages=messages)
        store.event(task['id'],'review_decision',{'decision':'request_changes','reason':step['request'],'transport':'recorded_director_diagnostic'})
    engine=Engine(store);started=time.monotonic()
    print(json.dumps({'task_id':task['id'],'state':'running'}),flush=True)
    try:
        await asyncio.wait_for(engine.run(task['id']),timeout=420)
    except TimeoutError:
        store.update(task['id'],state='paused',result='Acceptance deadline reached; not verified.')
    finally:
        final=store.get(task['id']);actions=store.actions(task['id'])
        result={'task_id':task['id'],'supervision':'none' if args.autonomous else 'recorded_director','state':final['state'],'result':final['result'],
                'elapsed_seconds':round(time.monotonic()-started,2),'actions':actions,'events':store.events(task['id'])}
        suffix='-revision-'+str(final['revision']) if args.resume_task else ''
        output=ROOT/(task['id']+suffix+'.json');output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k not in ('actions','events')},ensure_ascii=False),flush=True)
        print(str(output),flush=True)

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
