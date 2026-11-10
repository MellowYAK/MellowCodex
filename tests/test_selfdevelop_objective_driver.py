"""Durable objective transitions use existing candidate and director review services."""
import asyncio
from hub.store import Store, Conflict
from hub.development.selfdevelop import SelfDevelop


class FakeDevelopment:
    def __init__(self):
        self.created=0
        self.repaired=0
    def create(self,task):
        self.created+=1
        return {'id':'a'*32,'revision':0}
    def inspect(self,task,candidate_id):
        assert candidate_id=='a'*32
        return {'revision':1,'files':{'hub/a.py':'a'*64},
                'test_results':[{'revision':1,'verified':True,'evidence':'observed-test.json'}]}
    async def repair(self,task,candidate_id,revision,paths,tests,model=None,max_attempts=1):
        self.repaired+=1
        assert candidate_id=='a'*32 and revision==0 and paths==['hub/a.py']
        return {'candidate_id':candidate_id,'revision':1,
                'test':{'verified':True,'evidence':'observed-test.json','exit_code':0},
                'stop_reason':'tests_passed'}


def setup(tmp_path):
    store=Store(tmp_path/'hub.db')
    service=SelfDevelop(store)
    chat=service.start('One original repair objective','test:objective-flow','mcp')['chat_id']
    task=service.step(chat,'read-first','Read scoped source',['project_brief'],context_read={'operation':'brief'})
    store.update(task['id'],state='waiting_review')
    return store,service,chat,task


def test_authorized_objective_drives_candidate_repair_and_pauses_for_review(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    run=svc.authorize_objective(chat,task['id'],'single-authorized-run-001',
            ['hub/a.py'],['tests/test_a.py'],'qwen2.5-coder:7b',2,'gpt',False)
    assert run['phase']=='repair_queued'
    dev=FakeDevelopment()
    result=asyncio.run(svc.advance_objective(chat,dev))
    assert result['phase']=='semantic_review_required'
    assert result['candidate_id']=='a'*32 and result['candidate_revision']==1
    assert result['test_evidence']=='observed-test.json'
    assert dev.created==1 and dev.repaired==1
    after_restart=SelfDevelop(Store(tmp_path/'hub.db')).objective_status(chat)
    assert after_restart['phase']=='semantic_review_required'
    assert after_restart['original_objective']=='One original repair objective'
    assert after_restart['semantic_approved'] is False
    assert after_restart['update_id'] is None
    assert asyncio.run(SelfDevelop(store).advance_objective(chat,dev))['phase']=='semantic_review_required'
    assert dev.repaired==1


def test_pytest_success_never_approves_or_deploys(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    svc.authorize_objective(chat,task['id'],'single-authorized-run-002',
            ['hub/a.py'],['tests/test_a.py'],None,1,'gpt',True)
    dev=FakeDevelopment()
    asyncio.run(svc.advance_objective(chat,dev))
    status=svc.objective_status(chat)
    assert status['phase']=='semantic_review_required'
    assert status['semantic_approved'] is False
    assert status['update_id'] is None


def test_unsafe_inflight_restart_does_not_replay_repair(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    svc.authorize_objective(chat,task['id'],'single-authorized-run-003',
            ['hub/a.py'],['tests/test_a.py'],None,2,'local',False)
    with store.connect() as db:
        db.execute("UPDATE selfdevelop_objective_runs SET phase='repair_inflight' WHERE chat_id=?",(chat,))
    dev=FakeDevelopment()
    recovered=asyncio.run(SelfDevelop(Store(tmp_path/'hub.db')).advance_objective(chat,dev))
    assert recovered['phase']=='reconcile_required'
    assert dev.created==0 and dev.repaired==0
    assert recovered['semantic_approved'] is False


def test_objective_rejects_other_chat_task_and_changed_request(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    other=svc.start('Other project objective','test:other-objective','mcp')['chat_id']
    try:
        svc.authorize_objective(other,task['id'],'single-authorized-run-004',
            ['hub/a.py'],['tests/test_a.py'],None,1,'gpt',False)
    except Conflict:
        pass
    else:
        raise AssertionError('Must reject cross-chat task')
    svc.authorize_objective(chat,task['id'],'single-authorized-run-005',
            ['hub/a.py'],['tests/test_a.py'],None,1,'gpt',False)
    try:
        svc.authorize_objective(chat,task['id'],'single-authorized-run-005',
            ['hub/b.py'],['tests/test_a.py'],None,1,'gpt',False)
    except Conflict:
        pass
    else:
        raise AssertionError('Must reject changed request under idempotency key')


class FakeGuard:
    def __init__(self):
        self.prepares=[]
        self.launches=[]
        self.state='PREPARED'
    def prepare(self,dev,task,candidate,revision):
        self.prepares.append((task['id'],candidate,revision))
        return {'id':'d'*32,'state':'PREPARED'}
    def submit(self,update_id,request_id,recover=False):
        self.launches.append((update_id,request_id,recover))
        return {'id':update_id,'state':self.state}
    def find_prepared(self,dev,task,candidate_id,revision):
        assert candidate_id=='a'*32 and revision==1
        if len(self.prepares)!=1:
            raise ValueError('No unique matching Guard journal')
        return {'id':'d'*32,'state':self.state}

    def status(self,update_id):
        return {'id':update_id,'state':self.state,
                'supervisor_pid':12345 if self.launches else None}


def test_review_then_guard_activation_then_reconnect_verifies_same_chat(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    svc.authorize_objective(chat,task['id'],'single-authorized-run-006',
        ['hub/a.py'],['tests/test_a.py'],None,2,'gpt',True)
    dev=FakeDevelopment()
    guard=FakeGuard()
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='semantic_review_required'
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='semantic_review_required'
    assert guard.prepares==[] and guard.launches==[]
    store.update(task['id'],state='done')
    store.event(task['id'],'review_decision',{'decision':'approve','reason':'Verified source diff and semantic intent'})
    svc.bind_objective_review(task['id'],dev)
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='guard_prepare_queued'
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='guard_activation_queued'
    assert guard.prepares==[(task['id'],'a'*32,1)]
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='activation_requested'
    assert len(guard.launches)==1 and guard.launches[0][0]=='d'*32
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='activation_requested'
    assert len(guard.launches)==1
    guard.state='ACTIVE_VERIFIED'
    reconnected=SelfDevelop(Store(tmp_path/'hub.db'))
    status=asyncio.run(reconnected.advance_objective(chat,dev,guard))
    assert status['phase']=='active_verified'
    assert status['update_id']=='d'*32
    assert status['semantic_approved'] is True
    assert status['original_objective']=='One original repair objective'
    assert len(guard.launches)==1 and dev.repaired==1


def test_guard_never_runs_for_local_policy_without_explicit_authorization(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    svc.authorize_objective(chat,task['id'],'single-authorized-run-007',
        ['hub/a.py'],['tests/test_a.py'],None,1,'local',False)
    dev=FakeDevelopment()
    guard=FakeGuard()
    asyncio.run(svc.advance_objective(chat,dev,guard))
    store.update(task['id'],state='done')
    store.event(task['id'],'review_decision',{'decision':'approve','reason':'Local evidence inspected'})
    svc.bind_objective_review(task['id'],dev)
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='approved_not_deployed'
    assert guard.prepares==[] and guard.launches==[]


def test_old_review_before_model_repair_cannot_approve_new_candidate(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    store.event(task['id'],'review_decision',{'decision':'approve','reason':'Earlier mapping review'})
    svc.authorize_objective(chat,task['id'],'single-authorized-run-008',
        ['hub/a.py'],['tests/test_a.py'],None,1,'gpt',True)
    dev=FakeDevelopment();guard=FakeGuard()
    asyncio.run(svc.advance_objective(chat,dev,guard))
    store.update(task['id'],state='done')
    assert svc.objective_status(chat)['semantic_approved'] is False
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='semantic_review_required'
    assert guard.prepares==[]


def test_background_driver_advances_authorized_run_without_manual_phase_dispatch(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    svc.authorize_objective(chat,task['id'],'single-authorized-run-009',
        ['hub/a.py'],['tests/test_a.py'],None,2,'gpt',True)
    dev=FakeDevelopment()
    guard=FakeGuard()

    async def run():
        watcher=asyncio.create_task(svc.watch_objectives(lambda:dev,lambda:guard,interval=0.01))
        try:
            for unused in range(100):
                if svc.objective_status(chat)['phase']=='semantic_review_required':
                    break
                await asyncio.sleep(0.01)
            assert svc.objective_status(chat)['phase']=='semantic_review_required'
            assert dev.repaired==1 and guard.prepares==[]
            store.update(task['id'],state='done')
            store.event(task['id'],'review_decision',{'decision':'approve','reason':'External GPT verified candidate diff'})
            svc.bind_objective_review(task['id'],dev)
            for unused in range(100):
                if svc.objective_status(chat)['phase']=='activation_requested':
                    break
                await asyncio.sleep(0.01)
            assert svc.objective_status(chat)['phase']=='activation_requested'
            assert len(guard.launches)==1
            guard.state='ACTIVE_VERIFIED'
            for unused in range(100):
                if svc.objective_status(chat)['phase']=='active_verified':
                    break
                await asyncio.sleep(0.01)
            assert svc.objective_status(chat)['phase']=='active_verified'
            assert len(guard.launches)==1
        finally:
            watcher.cancel()
            await asyncio.gather(watcher,return_exceptions=True)


def test_review_identity_must_match_candidate_revision_and_receipt(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    svc.authorize_objective(chat,task['id'],'single-authorized-run-010',
        ['hub/a.py'],['tests/test_a.py'],None,1,'gpt',True)
    dev=FakeDevelopment();guard=FakeGuard()
    asyncio.run(svc.advance_objective(chat,dev,guard))
    store.update(task['id'],state='done')
    store.event(task['id'],'review_decision',{'decision':'approve','reason':'External director review'})
    # A generic task review without exact candidate/receipt binding is not approval.
    assert svc.objective_status(chat)['semantic_approved'] is False
    svc.bind_objective_review(task['id'],dev)
    assert svc.objective_status(chat)['semantic_approved'] is True
    with store.connect() as db:
        db.execute('UPDATE selfdevelop_objective_runs SET candidate_revision=2 WHERE chat_id=?',(chat,))
    assert svc.objective_status(chat)['semantic_approved'] is False
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='reconcile_required'
    assert guard.prepares==[]


def test_cancelled_before_guard_prepare_must_not_launch(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    svc.authorize_objective(chat,task['id'],'single-authorized-run-011',
        ['hub/a.py'],['tests/test_a.py'],None,1,'gpt',True)
    dev=FakeDevelopment();guard=FakeGuard()
    asyncio.run(svc.advance_objective(chat,dev,guard))
    store.update(task['id'],state='done')
    store.event(task['id'],'review_decision',{'decision':'approve','reason':'Reviewed'})
    svc.bind_objective_review(task['id'],dev)
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='guard_prepare_queued'
    store.update(task['id'],state='cancelled')
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='stopped'
    assert guard.prepares==[] and guard.launches==[]


def test_interrupted_guard_prepare_recovers_unique_journal_identity(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    svc.authorize_objective(chat,task['id'],'single-authorized-run-012',
        ['hub/a.py'],['tests/test_a.py'],None,1,'gpt',True)
    dev=FakeDevelopment();guard=FakeGuard()
    asyncio.run(svc.advance_objective(chat,dev,guard))
    store.update(task['id'],state='done')
    store.event(task['id'],'review_decision',{'decision':'approve','reason':'Reviewed'})
    svc.bind_objective_review(task['id'],dev)
    asyncio.run(svc.advance_objective(chat,dev,guard))
    store.event(task['id'],'selfdevelop_guard_prepare_intent',
        {'candidate_id':'a'*32,'revision':1,'evidence':'observed-test.json',
         'files_sha256':'verified-test-fingerprint'})
    with store.connect() as db:
        db.execute("UPDATE selfdevelop_objective_runs SET phase='guard_preparing' WHERE chat_id=?",(chat,))
    guard.prepares.append((task['id'],'a'*32,1))
    resumed=SelfDevelop(Store(tmp_path/'hub.db'))
    assert asyncio.run(resumed.advance_objective(chat,dev,guard))['phase']=='guard_activation_queued'
    assert resumed.objective_status(chat)['update_id']=='d'*32
    assert len(guard.prepares)==1


def test_guard_rollback_is_known_terminal_failure_not_uncertain(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    svc.authorize_objective(chat,task['id'],'single-authorized-run-013',
        ['hub/a.py'],['tests/test_a.py'],None,1,'gpt',True)
    dev=FakeDevelopment();guard=FakeGuard()
    asyncio.run(svc.advance_objective(chat,dev,guard))
    store.update(task['id'],state='done')
    store.event(task['id'],'review_decision',{'decision':'approve','reason':'Reviewed'})
    svc.bind_objective_review(task['id'],dev)
    asyncio.run(svc.advance_objective(chat,dev,guard))
    asyncio.run(svc.advance_objective(chat,dev,guard))
    asyncio.run(svc.advance_objective(chat,dev,guard))
    guard.state='ROLLED_BACK'
    result=asyncio.run(svc.advance_objective(chat,dev,guard))
    assert result['phase']=='rolled_back'
    assert 'ROLLED_BACK' in result['error']
    assert len(guard.launches)==1


def test_verified_update_creates_idempotent_terminal_chat_turn(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    svc.authorize_objective(chat,task['id'],'single-authorized-run-014',
        ['hub/a.py'],['tests/test_a.py'],None,1,'gpt',True)
    dev=FakeDevelopment();guard=FakeGuard()
    asyncio.run(svc.advance_objective(chat,dev,guard))
    store.update(task['id'],state='done')
    store.event(task['id'],'review_decision',{'decision':'approve','reason':'Reviewed'})
    svc.bind_objective_review(task['id'],dev)
    for n in range(3):
        asyncio.run(svc.advance_objective(chat,dev,guard))
    guard.state='ACTIVE_VERIFIED'
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='active_verified'
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='reported'
    report_id=svc.objective_status(chat)['report_task_id']
    assert report_id
    assert 'ACTIVE_VERIFIED' in store.get(report_id)['result']
    assert store.get(report_id)['state']=='done'
    assert len(SelfDevelop(Store(tmp_path/'hub.db')).status(chat)['objective_run']['report_task_id'])>0
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='reported'
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM chat_tasks WHERE chat_id=? AND task_id=?", (chat,report_id)).fetchone()[0]==1


def test_objective_approval_binding_failure_keeps_reviewable_task(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    svc.authorize_objective(chat,task['id'],'single-authorized-run-015',
        ['hub/a.py'],['tests/test_a.py'],None,1,'gpt',True)
    dev=FakeDevelopment()
    asyncio.run(svc.advance_objective(chat,dev))
    original_revision=store.get(task['id'])['revision']
    # The model candidate was repaired, but its matching test evidence is absent.
    class MissingReceipt(FakeDevelopment):
        def inspect(self,task,candidate_id):
            manifest=super().inspect(task,candidate_id)
            manifest['test_results']=[]
            return manifest
    try:
        svc.commit_objective_review(task['id'],original_revision,
            'Director reviewed the candidate',MissingReceipt())
    except Conflict:
        pass
    else:
        raise AssertionError('Invalid artifact binding must reject approval')
    assert store.get(task['id'])['state']=='waiting_review'
    assert store.get(task['id'])['revision']==original_revision
    assert store.latest_event(task['id'],'review_decision') is None
    assert store.latest_event(task['id'],'selfdevelop_objective_review_bound') is None
    approved=svc.commit_objective_review(task['id'],original_revision,
        'Director reviewed exact evidence',dev)
    assert approved['state']=='done'
    assert svc.objective_status(chat)['semantic_approved'] is True


def test_rollback_reports_once_after_restart_in_original_chat(tmp_path):
    store,svc,chat,task=setup(tmp_path)
    svc.authorize_objective(chat,task['id'],'single-authorized-run-016',
        ['hub/a.py'],['tests/test_a.py'],None,1,'gpt',True)
    dev=FakeDevelopment();guard=FakeGuard()
    asyncio.run(svc.advance_objective(chat,dev,guard))
    store.update(task['id'],state='done')
    store.event(task['id'],'review_decision',{'decision':'approve','reason':'Director inspected'})
    svc.bind_objective_review(task['id'],dev)
    for _ in range(3):
        asyncio.run(svc.advance_objective(chat,dev,guard))
    assert svc.objective_status(chat)['phase']=='activation_requested'
    guard.state='ROLLED_BACK'
    assert asyncio.run(svc.advance_objective(chat,dev,guard))['phase']=='rolled_back'
    resumed=SelfDevelop(Store(tmp_path/'hub.db'))
    reported=asyncio.run(resumed.advance_objective(chat,dev,guard))
    assert reported['phase']=='reported'
    assert reported['update_id']=='d'*32
    text=store.get(reported['report_task_id'])['result']
    assert 'ROLLED_BACK' in text and 'not verified' in text
    assert 'a'*32 in text and 'revision 1' in text and 'd'*32 in text
    assert asyncio.run(resumed.advance_objective(chat,dev,guard))['report_task_id']==reported['report_task_id']
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM chat_tasks WHERE chat_id=? AND task_id=?',
                          (chat,reported['report_task_id'])).fetchone()[0]==1
    assert len(guard.launches)==1
