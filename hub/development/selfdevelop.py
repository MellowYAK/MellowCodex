"""Persistent, director-controlled development sessions for the Hub itself.

This is an orchestration mode, not a control-plane deployment supervisor.
"""
from pathlib import Path
import asyncio
import json
import hashlib
from ..conversations import Conversations
from ..store import Conflict, now
from .guidance import Guidance


class SelfDevelop:
    def __init__(self, store):
        self.store = store
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS selfdevelop_sessions (chat_id TEXT PRIMARY KEY, objective TEXT NOT NULL, transport TEXT NOT NULL, created TEXT NOT NULL)')
            db.execute("CREATE TABLE IF NOT EXISTS selfdevelop_objective_runs (chat_id TEXT PRIMARY KEY, request_id TEXT NOT NULL, task_id TEXT NOT NULL, phase TEXT NOT NULL, plan TEXT NOT NULL, candidate_id TEXT, candidate_revision INTEGER, test_evidence TEXT, update_id TEXT, report_task_id TEXT, error TEXT NOT NULL DEFAULT '', updated TEXT NOT NULL)")

    def start(self, objective, conversation_key, transport):
        if not isinstance(objective, str) or not objective.strip():
            raise ValueError('An explicit human objective is required')
        if transport not in ('mcp', 'play'):
            raise ValueError('Director transport must be mcp or play')
        chats = Conversations(self.store)
        project = chats.project(str(Path(__file__).resolve().parents[2]), 'MellowCodex')
        chat = chats.create(project['id'], 'SelfDevelop: ' + objective[:55], conversation_key)
        with self.store.connect() as db:
            old = db.execute('SELECT * FROM selfdevelop_sessions WHERE chat_id=?', (chat['id'],)).fetchone()
            if old and (old['objective'] != objective or old['transport'] != transport):
                raise Conflict('Existing SelfDevelop session has another objective or transport')
            db.execute('INSERT OR IGNORE INTO selfdevelop_sessions VALUES(?,?,?,?)', (chat['id'], objective, transport, now()))
        return self.status(chat['id'])

    def _progress(self, chat_id, last):
        """Project existing chat-scoped candidate/test events for safe resume."""
        with self.store.connect() as db:
            rows = db.execute("""
                SELECT e.kind,e.data FROM events e
                JOIN chat_tasks c ON c.task_id=e.task_id
                WHERE c.chat_id=? AND e.kind IN
                    ('candidate_created','candidate_staged','candidate_tested',
                     'coding_worker_finished','coding_worker_test_feedback')
                ORDER BY e.seq DESC LIMIT 300
            """, (chat_id,)).fetchall()
        events=[(r['kind'],json.loads(r['data'])) for r in rows]
        current=next((data.get('candidate_id') for kind,data in events
                      if data.get('candidate_id') and kind in
                      ('candidate_created','candidate_staged','candidate_tested',
                       'coding_worker_finished','coding_worker_test_feedback')),None)
        related=[(kind,data) for kind,data in events if data.get('candidate_id')==current]
        revision=next((data['revision'] for kind,data in related
                       if isinstance(data.get('revision'),int)),None)
        tested=next((data for kind,data in related
                     if kind=='candidate_tested' and data.get('revision')==revision),None)
        feedback=next((data for kind,data in related
                       if kind=='coding_worker_test_feedback'),None)
        state=last['state'] if last else 'waiting_director'
        review=self.store.latest_event(last['id'],'review_decision') if last else None
        approved=bool(state=='done' and review and review['data'].get('decision')=='approve')
        phase={'waiting_review':'semantic_review_required',
               'waiting_user':'director_correction_required',
               'failed':'failed_step_review_required',
               'running':'executing',
               'queued':'queued',
               'done':'waiting_director',
               'cancelled':'waiting_director'}.get(state,'waiting_director')
        return {'phase':phase,'candidate_id':current,'candidate_revision':revision,
                'test':({'verified':bool(tested.get('verified')),
                         'evidence':tested.get('evidence')} if tested else None),
                'feedback':({'next_attempt':feedback.get('next_attempt'),
                             'evidence':feedback.get('evidence')} if feedback else None),
                'semantic_approved':approved,
                'deployment_verified':None}

    def objective_status(self, chat_id):
        """Durable cursor from the existing task, candidate and event journal."""
        session=self.status(chat_id)
        with self.store.connect() as db:
            row=db.execute('SELECT * FROM selfdevelop_objective_runs WHERE chat_id=?',(chat_id,)).fetchone()
        if not row:
            return {'chat_id':chat_id,'original_objective':session['objective'],
                    'phase':'not_authorized','candidate_id':None,'candidate_revision':None,
                    'update_id':None,'semantic_approved':False}
        run=dict(row);run['plan']=json.loads(run['plan'])
        task=self.store.get(run['task_id'])
        decision=self.store.latest_event(run['task_id'],'review_decision')
        repaired=self.store.latest_event(run['task_id'],'selfdevelop_objective_repair_result')
        bound=self.store.latest_event(run['task_id'],'selfdevelop_objective_review_bound')
        run['semantic_approved']=bool(task['state']=='done' and decision and repaired and bound
            and decision['seq']>repaired['seq'] and bound['seq']>decision['seq']
            and decision['data'].get('decision')=='approve'
            and bound['data'].get('review_seq')==decision['seq']
            and bound['data'].get('candidate_id')==run['candidate_id']
            and bound['data'].get('candidate_revision')==run['candidate_revision']
            and bound['data'].get('test_evidence')==run['test_evidence'])
        run['original_objective']=session['objective']
        return run

    def bind_objective_review(self,task_id,development):
        """Bind an existing explicit director approval to verified exact artifacts."""
        with self.store.connect() as db:
            row=db.execute('SELECT * FROM selfdevelop_objective_runs WHERE task_id=?',(task_id,)).fetchone()
        if not row:
            return None
        run=dict(row)
        if run['phase']!='semantic_review_required':
            raise Conflict('Objective is not awaiting this semantic review')
        task=self.store.get(task_id)
        review=self.store.latest_event(task_id,'review_decision')
        repaired=self.store.latest_event(task_id,'selfdevelop_objective_repair_result')
        if task['state']!='done' or not review or not repaired or review['seq']<=repaired['seq'] or review['data'].get('decision')!='approve':
            raise Conflict('A newer explicit director approval is required')
        current=development.inspect(task,run['candidate_id'])
        if current['revision']!=run['candidate_revision']:
            raise Conflict('Candidate revision changed after tests')
        evidence=next((e for e in current.get('test_results',[])
                       if e.get('revision')==run['candidate_revision']
                       and e.get('verified') and e.get('evidence')==run['test_evidence']),None)
        if not evidence:
            raise Conflict('Matching verified candidate test receipt missing')
        fingerprint=hashlib.sha256(json.dumps(current['files'],sort_keys=True).encode('utf-8')).hexdigest()
        result={'candidate_id':run['candidate_id'],
                'candidate_revision':run['candidate_revision'],
                'test_evidence':run['test_evidence'],
                'files_sha256':fingerprint,
                'review_seq':review['seq'],
                'repair_seq':repaired['seq']}
        self.store.event(task_id,'selfdevelop_objective_review_bound',result)
        return result

    def has_objective_run(self, task_id):
        with self.store.connect() as db:
            return bool(db.execute('SELECT 1 FROM selfdevelop_objective_runs WHERE task_id=?',
                                   (task_id,)).fetchone())

    def commit_objective_review(self, task_id, expected_revision, reason, development):
        """Atomically approve an exactly verified candidate and bind its evidence.

        Ordinary non-objective task reviews stay on the existing route.
        """
        if not isinstance(reason,str) or not reason.strip():
            raise ValueError('Director review reason required')
        with self.store.connect() as db:
            run=db.execute('SELECT * FROM selfdevelop_objective_runs WHERE task_id=?',
                           (task_id,)).fetchone()
        if not run:
            raise Conflict('Objective run missing')
        if run['phase']!='semantic_review_required':
            raise Conflict('Objective not awaiting semantic review')
        task=self.store.get(task_id)
        if task['state']!='waiting_review' or task['revision']!=expected_revision:
            raise Conflict('Task review revision or state changed')
        current=development.inspect(task,run['candidate_id'])
        if current['revision']!=run['candidate_revision']:
            raise Conflict('Candidate revision changed after tests')
        receipt=next((r for r in current.get('test_results',[])
                      if r.get('revision')==run['candidate_revision'] and
                      r.get('verified') and r.get('evidence')==run['test_evidence']),None)
        if not receipt:
            raise Conflict('Matching candidate test evidence not found')
        fingerprint=hashlib.sha256(json.dumps(current['files'],sort_keys=True).encode('utf-8')).hexdigest()
        stamp=now()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM selfdevelop_objective_runs WHERE task_id=?',
                           (task_id,)).fetchone()
            current_task=db.execute('SELECT state,revision FROM tasks WHERE id=?',
                                    (task_id,)).fetchone()
            repaired=db.execute("SELECT seq FROM events WHERE task_id=? AND kind='selfdevelop_objective_repair_result' ORDER BY seq DESC LIMIT 1",(task_id,)).fetchone()
            if (not row or row['phase']!='semantic_review_required' or
                row['candidate_id']!=run['candidate_id'] or
                row['candidate_revision']!=run['candidate_revision'] or
                row['test_evidence']!=run['test_evidence'] or
                not current_task or current_task['state']!='waiting_review' or
                current_task['revision']!=expected_revision or not repaired):
                raise Conflict('Objective, revision or repair evidence changed before review commit')
            if db.execute("SELECT 1 FROM actions WHERE task_id=? AND state='pending' LIMIT 1",(task_id,)).fetchone():
                raise Conflict('Reconcile uncertain action before review commit')
            revision=expected_revision+1
            db.execute('UPDATE tasks SET state=?,revision=?,updated=? WHERE id=?',
                       ('done',revision,stamp,task_id))
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,?,?,?,?)',
                       (task_id,revision,'review',json.dumps({'state':'done'}),stamp))
            payload={'decision':'approve','expected_revision':expected_revision,
                     'reason':reason,'resume_handoff':False}
            review=db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,?,?,?,?)',
                              (task_id,revision,'review_decision',json.dumps(payload),stamp))
            bound={'candidate_id':run['candidate_id'],
                   'candidate_revision':run['candidate_revision'],
                   'test_evidence':run['test_evidence'],
                   'files_sha256':fingerprint,
                   'review_seq':review.lastrowid,'repair_seq':repaired['seq']}
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,?,?,?,?)',
                       (task_id,revision,'selfdevelop_objective_review_bound',
                        json.dumps(bound),stamp))
        return self.store.get(task_id)

    def authorize_objective(self,chat_id,task_id,request_id,paths,tests,
                            model=None,max_attempts=1,director_mode='gpt',
                            deploy_after_review=False):
        """One immutable bounded repair plan, not an approval of its result."""
        self.status(chat_id)
        if not isinstance(request_id,str) or not 8<=len(request_id)<=100:
            raise ValueError('Stable request ID is required')
        if director_mode not in ('gpt','local') or type(max_attempts) is not int or not 1<=max_attempts<=3:
            raise ValueError('Invalid bounded director policy')
        if type(deploy_after_review) is not bool or (director_mode=='local' and deploy_after_review):
            raise ValueError('Local policy may not pre-authorize Guard')
        if not 1<=len(paths)<=10 or len(set(paths))!=len(paths) or not 1<=len(tests)<=30:
            raise ValueError('Choose bounded source and test paths')
        if set(paths).intersection(t.split('::')[0] for t in tests):
            raise ValueError('Acceptance tests must stay read-only')
        if any(not isinstance(x,str) or not x or x.startswith(('/',chr(92)))
               or '..' in x.replace(chr(92),'/').split('/') for x in paths+tests):
            raise ValueError('Relative authorized paths required')
        plan=json.dumps({'paths':paths,'tests':tests,'model':model,'max_attempts':max_attempts,
                         'director_mode':director_mode,'deploy_after_review':deploy_after_review},
                        sort_keys=True,ensure_ascii=False)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            owner=db.execute('SELECT 1 FROM chat_tasks WHERE chat_id=? AND task_id=?',
                             (chat_id,task_id)).fetchone()
            if not owner:
                raise Conflict('Task belongs to a different chat')
            task=db.execute('SELECT state FROM tasks WHERE id=?',(task_id,)).fetchone()
            pending=db.execute("SELECT 1 FROM actions WHERE task_id=? AND state='pending' LIMIT 1",
                               (task_id,)).fetchone()
            if pending or not task or task['state']!='waiting_review':
                raise Conflict('Review mapping or reconcile pending actions before authorizing')
            old=db.execute('SELECT * FROM selfdevelop_objective_runs WHERE chat_id=?',(chat_id,)).fetchone()
            if old:
                if (old['request_id'],old['task_id'],old['plan'])!=(request_id,task_id,plan):
                    raise Conflict('Objective plan already exists with different arguments')
            else:
                db.execute('INSERT INTO selfdevelop_objective_runs(chat_id,request_id,task_id,phase,plan,updated) VALUES(?,?,?,?,?,?)',
                           (chat_id,request_id,task_id,'repair_queued',plan,now()))
        if not old:
            self.store.event(task_id,'selfdevelop_objective_authorized',
                             {'chat_id':chat_id,'request_id':request_id,'policy':director_mode})
        return self.objective_status(chat_id)

    def _objective_move(self,chat_id,expected,phase,**fields):
        """Atomic compare-and-swap phase update with no side-effect replay."""
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            assignments=['phase=?','updated=?']+[k+'=?' for k in fields]
            args=[phase,now(),*fields.values(),chat_id,expected]
            cursor=db.execute('UPDATE selfdevelop_objective_runs SET '+','.join(assignments)+
                              ' WHERE chat_id=? AND phase=?',args)
            if cursor.rowcount!=1:
                raise Conflict('Objective phase changed; inspect before retry')
        return self.objective_status(chat_id)

    async def advance_objective(self,chat_id,development,guardian=None):
        """Drive a permitted repair to semantic review; never approve pytest results."""
        run=self.objective_status(chat_id)
        phase=run['phase']
        if phase not in ('not_authorized','reported','stopped','repair_failed',
                         'reconcile_required','rolled_back','approved_not_deployed'):
            task=self.store.get(run['task_id'])
            if task['state'] in ('cancelled','paused','failed'):
                return self._objective_move(chat_id,phase,'stopped',
                    error='Original task stopped: '+task['state'])
            if any(action['state']=='pending' for action in self.store.actions(task['id'])):
                return self._objective_move(chat_id,phase,'reconcile_required',
                    error='Uncertain action blocks objective continuation')
        if phase in ('repair_inflight','candidate_creating'):
            return self._objective_move(chat_id,phase,'reconcile_required',
                                        error='Interrupted action; inspect candidate and audit')
        if phase=='repair_queued':
            task=self.store.get(run['task_id'])
            if task['state']!='waiting_review':
                return self._objective_move(chat_id,phase,'stopped',
                    error='Source task no longer reviewable')
            if any(a['state']=='pending' for a in self.store.actions(task['id'])):
                return self._objective_move(chat_id,phase,'reconcile_required',
                                            error='Uncertain pending action')
            candidate=run['candidate_id'];revision=run['candidate_revision']
            if candidate is None:
                self._objective_move(chat_id,'repair_queued','candidate_creating')
                created=development.create(task)
                candidate=created['id'];revision=created['revision']
                self._objective_move(chat_id,'candidate_creating','repair_queued',
                                     candidate_id=candidate,candidate_revision=revision)
            if self.store.get(task['id'])['state']!='waiting_review':
                return self._objective_move(chat_id,'repair_queued','stopped',
                    error='Original task changed before repair')
            self._objective_move(chat_id,'repair_queued','repair_inflight')
            plan=run['plan']
            try:
                outcome=await development.repair(task,candidate,revision,
                    plan['paths'],plan['tests'],plan['model'],plan['max_attempts'])
            except Exception as exc:
                return self._objective_move(chat_id,'repair_inflight','reconcile_required',
                                            error=str(exc)[:1000])
            if self.store.get(task['id'])['state']!='waiting_review':
                return self._objective_move(chat_id,'repair_inflight','stopped',
                    error='Original task changed during repair')
            receipt=outcome.get('test') or {}
            verified=bool(receipt.get('verified') and not receipt.get('timed_out')
                          and not receipt.get('source_changed'))
            self.store.event(task['id'],'selfdevelop_objective_repair_result',
                {'chat_id':chat_id,'candidate_id':candidate,'revision':outcome.get('revision'),
                 'verified':verified,'evidence':receipt.get('evidence')})
            return self._objective_move(chat_id,'repair_inflight',
                'semantic_review_required' if verified else 'repair_failed',
                candidate_revision=outcome.get('revision'),
                test_evidence=receipt.get('evidence'))
        if phase=='semantic_review_required':
            bound=self.store.latest_event(run['task_id'],'selfdevelop_objective_review_bound')
            if bound and (bound['data'].get('candidate_id')!=run['candidate_id']
                or bound['data'].get('candidate_revision')!=run['candidate_revision']
                or bound['data'].get('test_evidence')!=run['test_evidence']):
                return self._objective_move(chat_id,phase,'reconcile_required',
                    error='Semantic review identity differs from current artifact')
            if not run['semantic_approved']:
                return run
            if run['plan']['deploy_after_review']:
                return self._objective_move(chat_id,phase,'guard_prepare_queued')
            return self._objective_move(chat_id,phase,'approved_not_deployed')
        if phase=='guard_preparing':
            task=self.store.get(run['task_id'])
            intent=self.store.latest_event(task['id'],'selfdevelop_guard_prepare_intent')
            if not intent or any(intent['data'].get(k)!=v for k,v in
                    (('candidate_id',run['candidate_id']),
                     ('revision',run['candidate_revision']),
                     ('evidence',run['test_evidence']))):
                return self._objective_move(chat_id,phase,'reconcile_required',
                    error='Guard prepare intent missing or mismatched')
            if guardian is None:
                from ..guardian.control_plane_jobs import ControlPlaneJobs
                from ..config import ROOT
                guardian=ControlPlaneJobs(ROOT)
            try:
                journal=self.store.latest_event(task['id'],'selfdevelop_guard_prepared')
                if journal and journal['seq']>intent['seq'] and journal['data'].get('candidate_id')==run['candidate_id'] and journal['data'].get('revision')==run['candidate_revision']:
                    found=await asyncio.to_thread(guardian.status,journal['data']['update_id'])
                else:
                    found=await asyncio.to_thread(guardian.find_prepared,development,task,
                                                 run['candidate_id'],run['candidate_revision'])
            except Exception as exc:
                return self._objective_move(chat_id,phase,'reconcile_required',
                    error='Guard journal ambiguous: '+str(exc)[:600])
            if found['state']=='PREPARED':
                return self._objective_move(chat_id,phase,'guard_activation_queued',update_id=found['id'])
            if found['state']=='ACTIVE_VERIFIED':
                return self._objective_move(chat_id,phase,'active_verified',update_id=found['id'])
            if found['state']=='ROLLED_BACK':
                return self._objective_move(chat_id,phase,'rolled_back',
                    update_id=found['id'],error='Guard ROLLED_BACK: known failure')
            return self._objective_move(chat_id,phase,'reconcile_required',
                error='Guard journal requires inspection: '+str(found['state']))
        if phase in ('guard_prepare_queued','guard_activation_queued','activation_requested'):
            if not run['semantic_approved'] or not run['plan']['deploy_after_review']:
                return self._objective_move(chat_id,phase,'reconcile_required',
                                            error='Missing explicit director approval for Guard')
            task=self.store.get(run['task_id'])
            if any(a['state']=='pending' for a in self.store.actions(task['id'])):
                return self._objective_move(chat_id,phase,'reconcile_required',
                                            error='Uncertain pending action before Guard')
            if guardian is None:
                from ..guardian.control_plane_jobs import ControlPlaneJobs
                from ..config import ROOT
                guardian=ControlPlaneJobs(ROOT)
            if phase=='guard_prepare_queued':
                current=development.inspect(task,run['candidate_id'])
                bound=self.store.latest_event(task['id'],'selfdevelop_objective_review_bound')
                fingerprint=hashlib.sha256(json.dumps(current['files'],sort_keys=True).encode('utf-8')).hexdigest()
                if (not bound or current['revision']!=run['candidate_revision']
                    or bound['data'].get('files_sha256')!=fingerprint
                    or bound['data'].get('test_evidence')!=run['test_evidence']):
                    return self._objective_move(chat_id,phase,'reconcile_required',
                        error='Reviewed candidate fingerprint changed before Guard')
                self.store.event(task['id'],'selfdevelop_guard_prepare_intent',
                    {'candidate_id':run['candidate_id'],'revision':run['candidate_revision'],
                     'evidence':run['test_evidence'],'files_sha256':fingerprint})
                self._objective_move(chat_id,phase,'guard_preparing')
                try:
                    prepared=await asyncio.to_thread(guardian.prepare,development,task,
                        run['candidate_id'],run['candidate_revision'])
                except Exception as exc:
                    return self._objective_move(chat_id,'guard_preparing','reconcile_required',
                        error='Guard prepare requires journal reconciliation: '+str(exc)[:600])
                self.store.event(task['id'],'selfdevelop_guard_prepared',
                    {'candidate_id':run['candidate_id'],'revision':run['candidate_revision'],
                     'update_id':prepared['id']})
                return self._objective_move(chat_id,'guard_preparing','guard_activation_queued',
                                            update_id=prepared['id'])
            if phase=='guard_activation_queued':
                state=await asyncio.to_thread(guardian.status,run['update_id'])
                if state['state']!='PREPARED':
                    return self._objective_move(chat_id,phase,'reconcile_required',
                                                error='Guard no longer PREPARED; inspect update status')
                self._objective_move(chat_id,phase,'activation_requested')
                try:
                    await asyncio.to_thread(guardian.submit,run['update_id'],
                        'selfdevelop-'+chat_id,False)
                except Exception as exc:
                    self.store.event(task['id'],'selfdevelop_activation_uncertain',
                                     {'update_id':run['update_id'],'error':str(exc)[:650]})
                return self.objective_status(chat_id)
            observed=await asyncio.to_thread(guardian.status,run['update_id'])
            if observed['state']=='PREPARED' and not observed.get('supervisor_pid'):
                return self._objective_move(chat_id,phase,'reconcile_required',
                    error='Activation intent recorded but no supervisor launch; inspect journal')
            if observed['state']=='ACTIVE_VERIFIED':
                self.store.event(task['id'],'selfdevelop_objective_active_verified',
                                 {'chat_id':chat_id,'update_id':run['update_id']})
                return self._objective_move(chat_id,phase,'active_verified')
            if observed['state']=='ROLLED_BACK':
                return self._objective_move(chat_id,phase,'rolled_back',
                    error='Guard ROLLED_BACK: known failed deployment')
            if observed['state']=='RECOVERY_REQUIRED' or observed.get('recovery_required'):
                return self._objective_move(chat_id,phase,'reconcile_required',
                    error='Uncertain Guard outcome; explicit recovery required')
        if phase=='rolled_back':
            # A known rollback is a terminal outcome, not uncertain recovery.
            # Appending via the existing idempotent conversation API is safe
            # after a process restart and never resubmits activation.
            summary=('SelfDevelop Guard installation failed and was rolled back. '
                     'Original objective: '+run['original_objective']+
                     '. Candidate '+str(run['candidate_id'])+
                     ' revision '+str(run['candidate_revision'])+
                     ', test receipt '+str(run['test_evidence'])+
                     ', Guard update '+str(run['update_id'])+
                     ' ROLLED_BACK. Installation was not verified; inspect '
                     'the Guard journal before any new authorized attempt.')
            report_id=Conversations(self.store).append_objective_report(
                chat_id,run['request_id'],summary)
            result=self._objective_move(chat_id,phase,'reported',
                                        report_task_id=report_id)
            self.store.event(run['task_id'],'selfdevelop_objective_reported',
                             {'chat_id':chat_id,'report_task_id':report_id,
                              'update_id':run['update_id'],'outcome':'ROLLED_BACK'})
            return result
        if phase=='active_verified':
            if guardian is None:
                from ..guardian.control_plane_jobs import ControlPlaneJobs
                from ..config import ROOT
                guardian=ControlPlaneJobs(ROOT)
            observed=await asyncio.to_thread(guardian.status,run['update_id'])
            if observed['state']!='ACTIVE_VERIFIED':
                return self._objective_move(chat_id,phase,'reconcile_required',
                    error='Previously verified Guard state changed')
            summary=('SelfDevelop objective completed under explicit director review. '
                     'Original objective: '+run['original_objective']+
                     '. Candidate '+run['candidate_id']+' revision '+str(run['candidate_revision'])+
                     ', test receipt '+str(run['test_evidence'])+
                     ', Guard update '+run['update_id']+' ACTIVE_VERIFIED. '
                     'Supervised completion, not autonomous semantic approval.')
            report_id=Conversations(self.store).append_objective_report(
                chat_id,run['request_id'],summary)
            result=self._objective_move(chat_id,phase,'reported',report_task_id=report_id)
            self.store.event(run['task_id'],'selfdevelop_objective_reported',
                {'chat_id':chat_id,'report_task_id':report_id,'update_id':run['update_id']})
            return result
        return run

    async def watch_objectives(self,development_provider,guardian_factory=None,interval=2):
        """Advance safe persisted phases using existing Hub lifecycle."""
        while True:
            with self.store.connect() as db:
                chats=[r['chat_id'] for r in db.execute(
                    "SELECT chat_id FROM selfdevelop_objective_runs WHERE phase IN "
                    "('repair_queued','repair_inflight','candidate_creating',"
                    "'semantic_review_required','guard_prepare_queued','guard_preparing',"
                    "'guard_activation_queued','activation_requested','active_verified','rolled_back')")]
            for chat_id in chats:
                try:
                    await self.advance_objective(chat_id,development_provider(),
                        guardian_factory() if guardian_factory else None)
                except Exception as exc:
                    with self.store.connect() as db:
                        db.execute('UPDATE selfdevelop_objective_runs SET error=?,updated=? WHERE chat_id=?',
                                   (str(exc)[:1000],now(),chat_id))
            await asyncio.sleep(interval)

    def status(self, chat_id):
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM selfdevelop_sessions WHERE chat_id=?', (chat_id,)).fetchone()
            objective_run = db.execute('SELECT phase,report_task_id,update_id FROM selfdevelop_objective_runs WHERE chat_id=?', (chat_id,)).fetchone()
        if not row:
            raise KeyError('SelfDevelop session not found')
        chat = Conversations(self.store).get(chat_id)
        last = chat['turns'][-1] if chat['turns'] else None
        return {**dict(row), 'mode': 'selfdevelop', 'director': 'external',
                'executor': 'local', 'state': last['state'] if last else 'waiting_director',
                'task_id': last['id'] if last else None,
                'task_revision': last['revision'] if last else None,
                'progress': self._progress(chat_id,last),
                 'objective_run': dict(objective_run) if objective_run else None,
                'next_action': ('Review recorded output before approving or correcting the same task.' if last and last['state'] == 'waiting_review' else 'Review failed-step evidence, then explicitly call selfdevelop_close_failed with reason and expected_revision.' if last and last['state'] == 'failed' else 'Supply one bounded instruction with explicit allowed tools.'),
                'control_plane_restart_supported': True,
                'supervisor': 'Mellow Guard',
                'autonomous_development_verified': False,
                'deployment_scope': 'Mellow Guard stages and restarts owned Hub/MCP services with health rollback; desktop and dependency upgrades are not included.'}

    def owns(self, task_id):
        with self.store.connect() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='chat_tasks'").fetchone():
                return False
            row = db.execute('SELECT s.chat_id FROM selfdevelop_sessions s JOIN chat_tasks c ON s.chat_id=c.chat_id WHERE c.task_id=?', (task_id,)).fetchone()
        return bool(row)

    def guard(self, task_id):
        if not self.owns(task_id):
            return
        with self.store.connect() as db:
            row=db.execute('SELECT chat_id,position FROM chat_tasks WHERE task_id=?',(task_id,)).fetchone()
            prior=db.execute("SELECT 1 FROM chat_tasks c JOIN tasks t ON t.id=c.task_id WHERE c.chat_id=? AND c.position<? AND t.state NOT IN ('done','cancelled')",(row['chat_id'],row['position'])).fetchone()
        if prior:
            raise Conflict('SelfDevelop requires director review of the previous step before execution')
        guidance = Guidance(self.store).status(task_id)['guidance']
        if not guidance or Guidance(self.store).allowed_tools(task_id) is None:
            raise Conflict('SelfDevelop waits for director guidance and an explicit tool scope before execution')

    def step(self, chat_id, request_id, instruction, allowed_tools, required_tools=None,
             required_sources=None, evidence_only=False, exact_patch=None, context_read=None):
        self.status(chat_id)
        chats = Conversations(self.store)
        chat = chats.get(chat_id)
        idem = 'chat:' + chat_id + ':' + request_id
        with self.store.connect() as db:
            retry = db.execute('SELECT id FROM tasks WHERE idem=?', (idem,)).fetchone()
        if not retry and any(t['state'] not in ('done', 'cancelled') for t in chat['turns']):
            raise Conflict('Review or correct the existing step before starting another SelfDevelop step')
        if not allowed_tools:
            raise ValueError('Director must provide explicit allowed tools')
        Guidance.validate_request(request_id,instruction,required_tools,required_sources,allowed_tools,evidence_only,exact_patch,context_read)
        task = chats.submit(chat_id, instruction, 'code', request_id)
        guide = Guidance(self.store)
        status = guide.status(task['id'])
        guide.submit(task['id'], task['revision'], status['guidance_revision'], status['consumer_epoch'],
                     request_id, instruction, required_tools=required_tools,
                     required_sources=required_sources, allowed_tools=allowed_tools,
                     evidence_only=evidence_only, exact_patch=exact_patch, context_read=context_read)
        self.guard(task['id'])
        return self.store.get(task['id'])

    def close_failed(self, chat_id, task_id, expected_revision, request_id, reason):
        """Explicit audited closure of a final failed step, without replaying actions."""
        if not isinstance(request_id, str) or not 8 <= len(request_id) <= 100:
            raise ValueError('Closure request identity is required')
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 8000:
            raise ValueError('Director review reason is required')
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError('Invalid expected revision')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            member=db.execute('''SELECT c.position FROM chat_tasks c
                JOIN selfdevelop_sessions s ON s.chat_id=c.chat_id
                WHERE c.chat_id=? AND c.task_id=?''',(chat_id,task_id)).fetchone()
            if not member:
                raise Conflict('Step is not owned by the specified SelfDevelop chat')
            task=db.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
            if not task:
                raise Conflict('Task no longer exists')
            rows=db.execute("SELECT data FROM events WHERE task_id=? AND kind='selfdevelop_failed_closed' ORDER BY seq",(task_id,)).fetchall()
            for row in rows:
                old=json.loads(row['data'])
                if old.get('request_id')==request_id:
                    if old.get('reason')!=reason or old.get('expected_revision')!=expected_revision:
                        raise Conflict('Closure identity reused with different content')
                    if task['state']!='cancelled':
                        raise Conflict('Previously closed task changed state')
                    return self.store._decode(task)
            if task['state']!='failed' or task['revision']!=expected_revision:
                raise Conflict('Only a current final failed task can be explicitly closed')
            if db.execute("SELECT 1 FROM actions WHERE task_id=? AND state='pending' LIMIT 1",(task_id,)).fetchone():
                raise Conflict('Pending or uncertain action requires reconciliation')
            if db.execute("""SELECT 1 FROM chat_tasks c JOIN tasks t ON t.id=c.task_id
                WHERE c.chat_id=? AND c.position>? AND t.state NOT IN ('done','cancelled') LIMIT 1""",
                          (chat_id,member['position'])).fetchone():
                raise Conflict('Resolve subsequent active or unreviewed steps first')
            stamp=now()
            revision=task['revision']+1
            db.execute("UPDATE tasks SET state='cancelled',revision=?,updated=? WHERE id=?",(revision,stamp,task_id))
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,?,?,?,?)',
                       (task_id,revision,'selfdevelop_failed_closed',
                        json.dumps({'chat_id':chat_id,'request_id':request_id,'reason':reason,
                                    'expected_revision':expected_revision,'previous_state':'failed',
                                    'actions_replayed':False},ensure_ascii=False),stamp))
        return self.store.get(task_id)
