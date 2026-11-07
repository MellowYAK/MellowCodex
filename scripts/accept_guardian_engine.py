"""Agent-owned benign self-candidate, tested stage, independent supervisor activation."""
import asyncio
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')


async def main():
    from hub.config import ROOT,STATE,OLLAMA
    if not os.environ.get('LOCAL_AGENT_ROOT') or ROOT.resolve()==Path('E:/AI').resolve():raise RuntimeError('Isolated audit root required')
    import httpx
    async with httpx.AsyncClient(trust_env=False) as client:
        if (await client.get(OLLAMA+'/api/ps')).json().get('models'):raise RuntimeError('Existing model workload; do not disrupt it')
    from hub.store import Store
    from hub.conversations import Conversations
    from hub.engine import Engine
    from hub.model_settings import ModelSettings,save_settings
    from hub.development.guidance import Guidance
    from hub.guardian.jobs import UpgradeJobs
    from hub.development.workspaces import sha
    source=Path(__file__).resolve().parents[1]
    original=sha((source/'hub/development/worker.py').read_bytes())
    save_settings(ModelSettings(visual_guidance=False,request_timeout_seconds=300,keep_alive_minutes=2))
    store=Store(STATE/'hub.sqlite3');chats=Conversations(store)
    project=chats.project(str(source));chat=chats.create(project['id'])
    goal='Development acceptance: create an isolated candidate of this Hub repository. Use candidate_repair with model qwen2.5-coder:7b, paths ["hub/development/worker.py"], tests ["tests/test_worker_health.py"] to add only the sentence "Worker release acceptance marker." to the module docstring, preserving all behavior. Preserve every test and all live source. After verified tests, enable the upgrades tool group, stage this exact tested candidate using candidate_stage_release, and request upgrade_activate with stable request_id "guardian-engine-acceptance". Poll upgrade_status until ACTIVE_VERIFIED, then report the exact release and evidence. Never edit the live workspace or change the guardian/dependencies. This is an authorized isolated test activation, not production deployment.'
    task=chats.submit(chat['id'],goal,'code','guardian-acceptance')
    Guidance(store).submit(task['id'],task['revision'],0,'','guard-required','Use the patch-only coder, preserve tests and live source, and complete staged worker activation.',required_tools=['candidate_repair','candidate_stage_release','upgrade_activate','upgrade_status'])
    engine=Engine(store);started=time.monotonic()
    try:
        try:await asyncio.wait_for(engine.run(task['id']),420)
        except TimeoutError:store.update(task['id'],state='paused',result='Acceptance deadline exceeded; inspect retained actions and guardian status before retrying')
        final=store.get(task['id']);actions=store.actions(task['id']);status=UpgradeJobs(ROOT).status()
        evidence={'task':final,'elapsed_seconds':round(time.monotonic()-started,2),'actions':actions,'guardian':status,'original_preserved':sha((source/'hub/development/worker.py').read_bytes())==original}
        (ROOT/'acceptance.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'task_id':task['id'],'state':final['state'],'elapsed':evidence['elapsed_seconds'],'original_preserved':evidence['original_preserved'],'tools':[a['tool'] for a in actions],'active':status['active']},ensure_ascii=False))
    finally:
        async with httpx.AsyncClient(timeout=120,trust_env=False) as client:
            for model in ('qwen3.5:4b','qwen2.5-coder:7b'):
                await client.post(OLLAMA+'/api/generate',json={'model':model,'keep_alive':0,'stream':False})
            print(json.dumps({'resident_models':(await client.get(OLLAMA+'/api/ps')).json()}))


asyncio.run(main())
