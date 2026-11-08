import json
from pathlib import Path
import pytest
from hub.guardian.control_plane import stage,activate,sha,read,install

class FakeServices:
    def __init__(self,health=(True,)):self.health=iter(health);self.stops=0;self.starts=0
    def idle(self):pass
    def stop(self):self.stops+=1
    def start(self):self.starts+=1
    def healthy(self):return next(self.health)

def prepared(tmp_path):
    root=tmp_path/'state';root.mkdir()
    live=tmp_path/'live';live.mkdir();(live/'app.py').write_text('version=1\n')
    source=tmp_path/'source';source.mkdir();(source/'app.py').write_text('version=2\n')
    files={'app.py':sha((source/'app.py').read_bytes())}
    result=stage(root,live,source,files,{'verified':True})
    return root/'control-plane-updates'/result['id'],live

def test_success_preserves_journal_and_is_idempotent(tmp_path):
    job,live=prepared(tmp_path);driver=FakeServices()
    assert activate(job,driver)['state']=='ACTIVE_VERIFIED'
    assert (live/'app.py').read_text()=='version=2\n'
    assert activate(job,driver)['state']=='ACTIVE_VERIFIED'
    assert driver.starts==1 and driver.stops==1

def test_bad_health_restores_original(tmp_path):
    job,live=prepared(tmp_path);driver=FakeServices((False,True))
    assert activate(job,driver)['state']=='ROLLED_BACK'
    assert (live/'app.py').read_text()=='version=1\n'
    assert driver.starts==2

def test_changed_live_file_prevents_stop(tmp_path):
    job,live=prepared(tmp_path);(live/'app.py').write_text('user_change=1\n')
    driver=FakeServices()
    with pytest.raises(ValueError,match='Live source changed'):activate(job,driver)
    assert driver.stops==0

def test_recover_interrupted_install(tmp_path):
    job,live=prepared(tmp_path);install(job,read(job))
    (job/'status.json').write_text(json.dumps({'state':'INSTALLING'}))
    assert activate(job,FakeServices(),recover=True)['state']=='ROLLED_BACK'
    assert (live/'app.py').read_text()=='version=1\n'

def test_invalid_python_never_staged(tmp_path):
    root=tmp_path/'root';root.mkdir();live=tmp_path/'live';live.mkdir();source=tmp_path/'source';source.mkdir()
    (source/'app.py').write_text("x='broken\n")
    with pytest.raises(SyntaxError):stage(root,live,source,{'app.py':sha((source/'app.py').read_bytes())},{'verified':True})
    assert not (root/'control-plane-updates').exists()

def test_backup_tampering_detected(tmp_path):
    job,live=prepared(tmp_path);(job/'old'/'app.py').write_text('tampered')
    with pytest.raises(ValueError,match='backup/content'):activate(job,FakeServices())
    assert (live/'app.py').read_text()=='version=1\n'


def test_active_work_prevents_shutdown(tmp_path):
    job,live=prepared(tmp_path)
    driver=FakeServices()
    def busy():raise ValueError('Active tasks')
    driver.idle=busy
    with pytest.raises(ValueError,match='Active tasks'):activate(job,driver)
    assert driver.stops==0 and (live/'app.py').read_text()=='version=1\n'

def test_task_admission_preserves_task_during_update(tmp_path,monkeypatch):
    import hub.engine as module
    from hub.store import Store
    store=Store(tmp_path/'tasks.db')
    task=store.create('Keep my work',str(tmp_path),'code','gate-task')
    monkeypatch.setattr(module,'STATE',tmp_path)
    (tmp_path/'control-plane-admission.json').write_text('{"update_id":"pending"}')
    engine=module.Engine(store)
    engine.enqueue(task['id'])
    assert store.get(task['id'])['state']=='paused'
    assert store.get(task['id'])['goal']=='Keep my work'
    assert not engine.jobs
