"""Real child-worker activation/health and rollback using isolated durable state.

No model inference. Agent-owned benign candidate acceptance is a separate gate.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hub.config import ROOT
from hub.guardian import Guardian
from hub.development.workspaces import Workspaces
from hub.development.worker_runner import health


async def main():
    if not os.environ.get('LOCAL_AGENT_ROOT') or ROOT.resolve()==Path('E:/AI').resolve():raise RuntimeError('Use isolated audit root')
    g=Guardian(ROOT);work=Workspaces(ROOT/'candidates')
    candidate=work.create(Path(__file__).resolve().parents[1])
    # Evidence here is explicitly a deployment diagnostic, not candidate test certification.
    release=g.stage(work.directory(candidate['id'],candidate),candidate['files'],{'verified':True,'kind':'diagnostic-source-copy-not-agent-test'})
    result=await g.activate(release['id'],health)
    with g.worker() as (directory,pointer):
        observed=await health(directory,pointer['release_id'],'independent-probe')
    # Wrong nonce simulates a process from a different activation attempt.
    attempts=0
    async def wrong(directory,release_id,nonce):
        nonlocal attempts
        attempts+=1
        data=await health(directory,release_id,nonce)
        if attempts==1:data['nonce']='stale'
        return data
    failed=await g.activate(release['id'],wrong)
    proof={'activation':result,'independent_probe':observed,'unhealthy_activation':failed,'current':g.status()}
    (ROOT/'acceptance.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps({'active':result['state'],'unhealthy':failed['state'],'current_release':g.pointer()['release_id']}))


asyncio.run(main())
