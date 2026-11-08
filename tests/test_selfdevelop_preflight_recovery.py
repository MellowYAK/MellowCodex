"""Evidence-gated preflight recovery; GPT director, never a local worker."""
import asyncio
import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from hub.store import Store, Conflict
from hub.development.selfdevelop import SelfDevelop

BUDGET = 'ValueError: Scoped work packet exceeds selected context budget; narrow source files'
CID='a'*32


def digest(data):
    return hashlib.sha256(data).hexdigest()


class RecoveryDevelopment:
    def __init__(self, tmp_path, candidate_revision=0, store=None):
        self.revision=candidate_revision
        self.store=store
        self.calls=[]
        self._lock=threading.RLock()
        self.root=tmp_path/'candidate'
        self.folder=self.root/'revision-x'
        self.workspaces=SimpleNamespace(
            candidate=lambda identifier: self.root,
            directory=lambda identifier,manifest: self.folder)
    def inspect(self, task, candidate_id):
        assert candidate_id==CID
        files={}
        for relative in ('hub/a.py','tests/test_a.py'):
            files[relative]=digest((self.folder/relative).read_bytes())
        return {'id':candidate_id,'revision':self.revision,'files':files,
                'candidate_path':str(self.folder)}
    async def test(self,task,candidate_id,revision,tests,timeout=120):
        self.calls.append((candidate_id,revision,list(tests)))
        receipt={'candidate_id':candidate_id,'revision':revision,'verified':True,
                 'exit_code':0,'timed_out':False,'source_changed':[],
                 'evidence':str(self.root/'test-recovery.json')}
        (self.root/'test-recovery.json').write_text(json.dumps(receipt),encoding='utf-8')
        self.store.event(task['id'],'candidate_tested',
            {'candidate_id':candidate_id,'revision':revision,'verified':True,
             'evidence':receipt['evidence']})
        return receipt


def setup(tmp_path, error=BUDGET, phase='reconcile_required', anchored=True):
    store=Store(tmp_path/'hub.db')
    svc=SelfDevelop(store)
    chat=svc.start('Original GPT human objective','test:recovery','mcp')['chat_id']
    task=svc.step(chat,'read-first','Read authorized code',['project_brief'],
                  context_read={'operation':'brief'})
    store.update(task['id'],state='waiting_review')
    svc.authorize_objective(chat,task['id'],'initial-request-20261108',
                            ['hub/a.py'],['tests/test_a.py'],None,2,'gpt',False)
    svc._objective_move(chat,'repair_queued','repair_inflight',
                        candidate_id=CID,candidate_revision=0)
    root=tmp_path/'candidate'
    raw={'hub/a.py':b'def example():\\n    return 1\\n',
         'tests/test_a.py':b'def test_a(): pass\\n'}
    sources={}
    for relative,content in raw.items():
        for suffix in ('source','revision-x'):
            dest=root/suffix/relative
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(content)
        sources[relative]={'sha256':digest(content),'text':content.decode(),'writable':relative=='hub/a.py'}
    packet={'task_id':task['id'],'candidate_id':CID,'candidate_revision':0,
            'sources':sources,'allowed_paths':['hub/a.py'],
            'acceptance_tests':['tests/test_a.py']}
    packet_file=root/'worker-packet.json'
    packet_file.write_bytes(json.dumps(packet).encode())
    meta={'candidate_id':CID,'revision':0,'packet':str(packet_file)}
    if anchored:
        meta['packet_sha256']=digest(packet_file.read_bytes())
        meta['source_sha256']={rel:info['sha256'] for rel,info in sources.items()}
    store.event(task['id'],'coding_worker_started',meta)
    svc._objective_move(chat,'repair_inflight',phase,error=error)
    return store,svc,chat,task

def test_narrow_no_effect_recovers_same_chat_without_runner_replay(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    dev=RecoveryDevelopment(tmp_path,store=store)
    result=asyncio.run(svc.recover_objective(chat,'recover-scope-20261108',
                'narrow','Preflight rejected context budget before source change',
                dev,expected_candidate_revision=0,
                paths=['hub/a.py'],tests=['tests/test_a.py']))
    assert result['phase']=='director_action_required'
    assert result['chat_id']==chat
    assert result['original_objective']=='Original GPT human objective'
    assert result['plan']['director_mode']=='gpt'
    assert dev.calls==[]
    # A guided narrow request MUST NOT dispatch local repair through the watcher.
    assert asyncio.run(svc.advance_objective(chat,dev))['phase']=='director_action_required'
    assert dev.calls==[]
    after_restart=SelfDevelop(Store(tmp_path/'hub.db')).objective_status(chat)
    assert after_restart['phase']=='director_action_required'
    assert after_restart['candidate_id']=='a'*32


def test_exact_guided_current_candidate_tests_once_and_requires_semantic_review(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    dev=RecoveryDevelopment(tmp_path,candidate_revision=2,store=store)
    result=asyncio.run(svc.recover_objective(chat,'recover-exact-20261108',
                'exact','Director staged focused patch, now verify selected tests',
                dev,expected_candidate_revision=2))
    assert result['phase']=='semantic_review_required'
    assert result['candidate_revision']==2
    assert result['test_evidence'].endswith('test-recovery.json')
    assert result['semantic_approved'] is False
    assert dev.calls==[('a'*32,2,['tests/test_a.py'])]
    reopened=SelfDevelop(Store(tmp_path/'hub.db'))
    again=asyncio.run(reopened.recover_objective(chat,'recover-exact-20261108',
                'exact','Director staged focused patch, now verify selected tests',
                dev,expected_candidate_revision=2))
    assert again['phase']=='semantic_review_required'
    assert len(dev.calls)==1


def test_stale_or_ambiguous_preflight_must_not_resume(tmp_path):
    store,svc,chat,task=setup(tmp_path,error='RuntimeError: worker state unknown')
    dev=RecoveryDevelopment(tmp_path)
    with pytest.raises(Conflict):
        asyncio.run(svc.recover_objective(chat,'recover-invalid-20261108',
                     'narrow','Only budget failures supported',dev,
                     expected_candidate_revision=0))
    assert svc.objective_status(chat)['phase']=='reconcile_required'
    assert dev.calls==[]


def test_narrow_refuses_changed_candidate_and_any_pending_action(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    changed=RecoveryDevelopment(tmp_path,candidate_revision=2)
    with pytest.raises(Conflict):
        asyncio.run(svc.recover_objective(chat,'recover-change-20261108',
                     'narrow','Cannot replay changed source',changed,
                     expected_candidate_revision=2))
    assert svc.objective_status(chat)['phase']=='reconcile_required'


def test_exact_rejects_altered_plan_and_stale_id_without_new_testing(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    dev=RecoveryDevelopment(tmp_path,candidate_revision=1,store=store)
    asyncio.run(svc.recover_objective(chat,'recover-once-20261108',
                'exact','Reviewed current candidate',dev,
                expected_candidate_revision=1))
    with pytest.raises(Conflict):
        asyncio.run(svc.recover_objective(chat,'recover-once-20261108',
                'exact','Modified meaning of recovery',dev,
                expected_candidate_revision=1))
    assert len(dev.calls)==1


def test_pending_uncertain_action_never_runs_guided_recovery(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    store.begin_action(task['id'],'run_shell',{'command':'inert'})
    dev=RecoveryDevelopment(tmp_path,store=store)
    with pytest.raises(Conflict,match='Uncertain pending'):
        asyncio.run(svc.recover_objective(chat,'recover-pending-20261108',
                    'narrow','Do not replay unknown action',dev,
                    expected_candidate_revision=0,paths=['hub/a.py'],
                    tests=['tests/test_a.py']))
    assert svc.objective_status(chat)['phase']=='reconcile_required'
    assert dev.calls==[]


def test_scoped_no_effect_retry_rejects_later_candidate_stage_event(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    store.event(task['id'],'candidate_staged',
        {'candidate_id':'a'*32,'revision':1,'paths':['hub/a.py']})
    dev=RecoveryDevelopment(tmp_path,store=store)
    with pytest.raises(Conflict,match='effects'):
        asyncio.run(svc.recover_objective(chat,'recover-stage-20261108',
                    'narrow','No replay after an observed source edit',dev,
                    expected_candidate_revision=0,paths=['hub/a.py'],
                    tests=['tests/test_a.py']))
    assert svc.objective_status(chat)['phase']=='reconcile_required'
    assert dev.calls==[]


def test_changed_file_same_manifest_revision_is_not_no_effect(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    changed=tmp_path/'candidate'/'revision-x'/'hub/a.py'
    changed.write_bytes(b'UNAUTHORIZED CHANGE')
    dev=RecoveryDevelopment(tmp_path,store=store)
    with pytest.raises(Conflict,match='bytes'):
        asyncio.run(svc.recover_objective(chat,'recover-bytes-20261108',
            'narrow','The same revision number is not a byte-level proof',
            dev,expected_candidate_revision=0))
    assert svc.objective_status(chat)['phase']=='reconcile_required'


def test_unanchored_legacy_packet_does_not_authorize_worker_retry(tmp_path):
    store,svc,chat,task=setup(tmp_path,anchored=False)
    dev=RecoveryDevelopment(tmp_path,store=store)
    with pytest.raises(Conflict,match='Authenticated failure-time packet digest'):
        asyncio.run(svc.recover_objective(chat,'recover-nohash-20261108',
            'narrow','No anchored failure-time digest',dev,
            expected_candidate_revision=0))
    assert svc.objective_status(chat)['phase']=='reconcile_required'


def test_packet_tamper_is_not_accepted_as_no_effect_evidence(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    packet=tmp_path/'candidate'/'worker-packet.json'
    packet.write_text(packet.read_text()+' ',encoding='utf-8')
    dev=RecoveryDevelopment(tmp_path,store=store)
    with pytest.raises(Conflict,match='digest'):
        asyncio.run(svc.recover_objective(chat,'recover-tamper-20261108',
            'narrow','Packet bytes must match the event',dev,
            expected_candidate_revision=0))


def test_narrow_then_exact_is_another_explicit_gpt_request(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    dev=RecoveryDevelopment(tmp_path,store=store)
    first=asyncio.run(svc.recover_objective(chat,'recover-narrow-20261108',
        'narrow','Director requests a non-automatic, narrower read',
        dev,expected_candidate_revision=0,paths=['hub/a.py'],tests=['tests/test_a.py']))
    assert first['phase']=='director_action_required'
    second=asyncio.run(svc.recover_objective(chat,'recover-after-narrow-20261108',
        'exact','Director explicitly verifies current bytes and required tests',
        dev,expected_candidate_revision=0))
    assert second['phase']=='semantic_review_required'
    assert len(dev.calls)==1


def test_atomic_exact_receipt_rolls_back_on_db_event_failure(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    dev=RecoveryDevelopment(tmp_path,store=store)
    with store.connect() as db:
        db.execute("""
            CREATE TRIGGER reject_repair_result BEFORE INSERT ON events
            WHEN NEW.kind='selfdevelop_objective_repair_result'
            BEGIN SELECT RAISE(ABORT,'synthetic transactional rejection'); END
        """)
    with pytest.raises(sqlite3.DatabaseError,match='synthetic transactional rejection'):
        asyncio.run(svc.recover_objective(chat,'recover-atomic-20261108',
            'exact','Director verifies atomic recovery evidence',dev,
            expected_candidate_revision=0))
    assert svc.objective_status(chat)['phase']=='recovery_testing'
    assert store.latest_event(task['id'],'selfdevelop_objective_repair_result') is None


def test_uncertain_worker_stage_rejected_even_in_exact_mode(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    store.event(task['id'],'candidate_staged',
                {'candidate_id':CID,'revision':1,'origin':'coding_worker'})
    dev=RecoveryDevelopment(tmp_path,candidate_revision=1,store=store)
    with pytest.raises(Conflict,match='effects'):
        asyncio.run(svc.recover_objective(chat,'recover-worker-stage-20261108',
            'exact','Cannot classify worker effect as a manual patch',dev,
            expected_candidate_revision=1))


def test_current_file_changed_during_test_cannot_commit_semantic_gate(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    class MutatingTest(RecoveryDevelopment):
        async def test(self,*args,**kwargs):
            result=await super().test(*args,**kwargs)
            (self.folder/'hub/a.py').write_bytes(b'CHANGED DURING TEST')
            return result
    dev=MutatingTest(tmp_path,store=store)
    with pytest.raises(Conflict,match='source hash'):
        asyncio.run(svc.recover_objective(chat,'recover-changing-20261108',
            'exact','Reject mutable artifact during tests',dev,
            expected_candidate_revision=0))
    assert svc.objective_status(chat)['phase']=='recovery_testing'
    assert store.latest_event(task['id'],'selfdevelop_objective_repair_result') is None


def test_unanchored_legacy_packet_rejects_exact_without_effects(tmp_path):
    store,svc,chat,task=setup(tmp_path,anchored=False)
    dev=RecoveryDevelopment(tmp_path,candidate_revision=2,store=store)
    before=svc.objective_status(chat)
    with pytest.raises(Conflict,match='Authenticated failure-time packet digest'):
        asyncio.run(svc.recover_objective(chat,'recover-exact-unanchored-20261108',
            'exact','Unanchored historical packet is not authenticated failure evidence',
            dev,expected_candidate_revision=2))
    after=svc.objective_status(chat)
    assert after['phase']==before['phase']=='reconcile_required'
    assert after['candidate_revision']==before['candidate_revision']
    assert after['test_evidence']==before['test_evidence']
    assert dev.calls==[]
    assert store.latest_event(task['id'],'selfdevelop_objective_recovery_requested') is None
    assert store.latest_event(task['id'],'selfdevelop_objective_repair_result') is None
