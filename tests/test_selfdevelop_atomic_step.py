"""Regression tests for SelfDevelop task/initial-guidance transaction."""
import sqlite3
import json
import pytest
from hub.store import Store, Conflict
from hub.development.selfdevelop import SelfDevelop
from hub.development.guidance import Guidance


def make_session(tmp_path):
    store=Store(tmp_path/'state.sqlite3')
    service=SelfDevelop(store)
    chat=service.start('Atomic SelfDevelop repair test','test:atomic-selfdevelop','mcp')
    return store,service,chat['chat_id']


def test_initial_guidance_committed_with_task_and_idempotent(tmp_path):
    store,service,chat=make_session(tmp_path)
    task=service.step(chat,'atomic-creation-001','Create bounded candidate',['candidate_create'])
    assert task['revision']==2 and task['state']=='queued'
    assert service.guard(task['id']) is None
    guidance=Guidance(store).status(task['id'])
    assert guidance['guidance_revision']==1
    assert json.loads(guidance['guidance'][0]['allowed_tools'])==['candidate_create']
    again=service.step(chat,'atomic-creation-001','Create bounded candidate',['candidate_create'])
    assert again['id']==task['id']
    assert Guidance(store).status(task['id'])['guidance_revision']==1


def test_validation_rejected_before_task_creation(tmp_path):
    store,service,chat=make_session(tmp_path)
    with pytest.raises(ValueError):
        service.step(chat,'invalid-guidance-001','Create bounded candidate',
                     ['candidate_create'],required_tools=['run_shell'])
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]==0


def test_failed_guidance_insert_rolls_back_every_row(tmp_path):
    store,service,chat=make_session(tmp_path)
    Guidance(store)
    with store.connect() as db:
        db.execute("""CREATE TRIGGER reject_initial_guide BEFORE INSERT ON development_guidance
            BEGIN SELECT RAISE(ABORT, 'synthetic guidance failure'); END""")
    with pytest.raises(sqlite3.IntegrityError):
        service.step(chat,'rollback-guidance-001','Create bounded candidate',['candidate_create'])
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM chat_tasks').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM events').fetchone()[0]==0


def test_blocker_diagnostics_and_safe_cancellation(tmp_path):
    store,service,chat=make_session(tmp_path)
    task=service.step(chat,'blocked-creation-001','First task',['candidate_create'])
    with pytest.raises(Conflict) as exc:
        service.step(chat,'blocked-creation-002','Second task',['candidate_create'])
    blocker=json.loads(str(exc.value))
    assert blocker['blocking_task_id']==task['id']
    assert blocker['state']=='queued' and blocker['revision']==2
    assert 'stop_task' in blocker['required_action']
    store.update(task['id'],expected=2,state='cancelled')
    next_task=service.step(chat,'blocked-creation-002','Second task',['candidate_create'])
    assert next_task['state']=='queued' and next_task['id']!=task['id']


def test_failed_task_requires_explicit_recovery_and_stale_guidance_rejected(tmp_path):
    store,service,chat=make_session(tmp_path)
    task=service.step(chat,'stale-creation-001','First task',['candidate_create'])
    with pytest.raises(Conflict):
        Guidance(store).submit(task['id'],1,1,'','stale-creation-001','Other instruction',
                               allowed_tools=['candidate_create'])
    failed=store.update(task['id'],expected=2,state='failed')
    with pytest.raises(Conflict) as exc:
        service.step(chat,'after-failure-001','Another step',['candidate_create'])
    blocker=json.loads(str(exc.value))
    assert blocker['state']=='failed' and blocker['revision']==failed['revision']
    assert 'selfdevelop_close_failed' in blocker['required_action']


def test_uncertain_effect_cannot_be_replayed_even_if_cancelled(tmp_path):
    store,service,chat=make_session(tmp_path)
    task=service.step(chat,'uncertain-creation-001','First task',['candidate_create'])
    store.update(task['id'],expected=2,state='cancelled')
    with store.connect() as db:
        db.execute("INSERT INTO actions(id,task_id,tool,args,state,created) VALUES(?,?,?,?,?,?)",
                   ('pending-action-001',task['id'],'run_shell','{}','pending','2026-01-01'))
    with pytest.raises(Conflict) as exc:
        service.step(chat,'uncertain-creation-002','Another step',['candidate_create'])
    blocker=json.loads(str(exc.value))
    assert blocker['blocking_task_id']==task['id']
    assert 'reconciled' in blocker['reason']
