import asyncio
import hashlib
import pytest
from hub.guardian import Guardian


def staged(tmp_path):
    source=tmp_path/'source';(source/'hub/development').mkdir(parents=True)
    p=source/'hub/development/worker.py';p.write_text('pass')
    g=Guardian(tmp_path/'runtime')
    manifest=g.stage(source,{'hub/development/worker.py':hashlib.sha256(p.read_bytes()).hexdigest()},{'verified':True})
    return g,manifest['id']


async def healthy(directory,release_id,nonce):return {'ready':True,'release_id':release_id,'nonce':nonce}


def test_activation_drains_and_checks_identity(tmp_path):
    g,identifier=staged(tmp_path)
    with g.worker():
        with pytest.raises(ValueError,match='busy'):asyncio.run(g.activate(identifier,healthy))
    assert not g.status()['updates']
    result=asyncio.run(g.activate(identifier,healthy,stabilization_seconds=0))
    assert result['state']=='ACTIVE_VERIFIED'
    with g.worker() as (directory,pointer):assert pointer['release_id']==identifier
    assert g.status()['active']['epoch']==1


def test_unhealthy_release_rolls_back_without_replacing_state(tmp_path):
    g,identifier=staged(tmp_path)
    state=g.root/'state';state.mkdir();sentinel=state/'user-work.txt';sentinel.write_text('keep')
    async def wrong(directory,release_id,nonce):
        if release_id=='baseline':return await healthy(directory,release_id,nonce)
        return {'ready':True,'release_id':identifier,'nonce':'old'}
    result=asyncio.run(g.activate(identifier,wrong))
    assert result['state']=='ROLLED_BACK'
    assert g.pointer()['release_id'] is None
    assert sentinel.read_text()=='keep'


@pytest.mark.parametrize('boundary',['PREPARED','DRAINED','BACKUP_VERIFIED','CANDIDATE_HEALTHY','SWITCHED','OBSERVING'])
def test_crash_boundary_recovers_old_route_before_worker_admission(tmp_path,boundary):
    g,identifier=staged(tmp_path)
    class Crash(BaseException):pass
    async def crash(state):
        if state==boundary:raise Crash()
    with pytest.raises(Crash):asyncio.run(g.activate(identifier,healthy,checkpoint=crash))
    restarted=Guardian(g.root)
    with pytest.raises(ValueError,match='recovery required'):
        with restarted.worker():pass
    assert asyncio.run(restarted.recover(healthy))['active']['release_id'] is None
    with restarted.worker() as (_,pointer):assert pointer['release_id'] is None
    assert restarted.status()['updates'][0]['state']=='ROLLED_BACK'


def test_tampered_release_never_routes(tmp_path):
    g,identifier=staged(tmp_path)
    (g.release(identifier)/'source/hub/development/worker.py').write_text('changed')
    with pytest.raises(ValueError,match='hash mismatch'):asyncio.run(g.activate(identifier,healthy))
    assert g.pointer()['release_id'] is None
