import asyncio
import threading
from hub.context.indexing import Indexing
from test_context_integration import service

def test_settings_do_not_schedule_and_explicit_request_preserves_disable(tmp_path):
    svc,p,_=service(tmp_path); queue=Indexing(svc)
    assert queue.settings(p['id'],False)['enabled'] is False
    assert asyncio.run(queue.once()) is False
    queue.request(p['id'])
    assert queue.status(p['id'])['enabled'] is False
    assert asyncio.run(queue.once()) is True
    assert queue.status(p['id'])['state']=='ready'

def test_direct_context_refresh_updates_shared_index_status(tmp_path):
    svc,p,_=service(tmp_path);queue=Indexing(svc)
    queue.settings(p['id'],False)
    result=svc.refresh(p['id'])
    status=queue.status(p['id'])
    assert status['state']=='ready' and status['result']['revision']==result['revision']
    assert status['enabled'] is False

def test_request_during_scan_is_not_lost(tmp_path):
    svc,p,_=service(tmp_path);queue=Indexing(svc)
    entered=threading.Event();release=threading.Event();original=svc.refresh
    def slow(project):
        result=original(project);entered.set()
        assert release.wait(5)
        return result
    svc.refresh=slow
    async def run():
        queue.request(p['id']);job=asyncio.create_task(queue.once())
        try:
            assert await asyncio.to_thread(entered.wait,5)
            queue.request(p['id'])
            assert not await queue.once()
        finally:
            release.set();await job
        assert queue.status(p['id'])['state']=='queued'
        assert await queue.once()
        assert queue.status(p['id'])['state']=='ready'
    asyncio.run(run())

def test_failed_job_can_be_requested_again(tmp_path):
    svc,p,_=service(tmp_path);queue=Indexing(svc);original=svc.refresh
    def fail(project):raise OSError('fixture unavailable')
    svc.refresh=fail;queue.request(p['id']);asyncio.run(queue.once())
    assert queue.status(p['id'])['state']=='failed'
    assert queue.status(p['id'])['result']['error']=='fixture unavailable'
    svc.refresh=original;queue.request(p['id']);asyncio.run(queue.once())
    assert queue.status(p['id'])['state']=='ready'

def test_idle_background_skips_content_scan_but_reconciles_periodically(tmp_path):
    svc,p,_=service(tmp_path);queue=Indexing(svc)
    queue.request(p['id']);asyncio.run(queue.once())
    original=svc.refresh;calls=[]
    def tracked(project):calls.append(project);return original(project)
    svc.refresh=tracked
    with queue.store.connect() as db:db.execute('UPDATE project_index_jobs SET updated=0')
    asyncio.run(queue.once());assert not calls
    assert 'metadata unchanged' in queue.status(p['id'])['result']['background_check']
    with queue.store.connect() as db:db.execute('UPDATE project_index_jobs SET updated=0,last_full=0')
    asyncio.run(queue.once());assert calls==[p['id']]

def test_background_detects_added_file_and_preserves_index_on_root_loss(tmp_path):
    from pathlib import Path
    svc,p,_=service(tmp_path);queue=Indexing(svc)
    queue.request(p['id']);asyncio.run(queue.once())
    root=Path(svc.project(p['id'])['path']);(root/'added.py').write_text('def added_function(): pass\n')
    with queue.store.connect() as db:db.execute('UPDATE project_index_jobs SET updated=0')
    asyncio.run(queue.once())
    assert queue.status(p['id'])['state']=='ready'
    previous=queue.status(p['id'])['last_full']
    root.rename(root.with_name('temporarily-unavailable'))
    with queue.store.connect() as db:db.execute('UPDATE project_index_jobs SET updated=0')
    asyncio.run(queue.once())
    result=queue.status(p['id'])
    assert result['state']=='failed' and result['last_full']==previous
    assert result['result']['automatic_retry_remaining']==2
