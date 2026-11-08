"""Serialized candidate writes with durable evidence in the existing task store."""
import json
import threading
from pathlib import Path
from .workspaces import Workspaces
from .contracts import PatchProposal
from .ownership import candidate_owner


def worker_guidance(snapshot):
    """Keep director instructions and constraints; omit archived executable payloads."""
    keys=('revision','request_id','text','required_sources','required_tools','allowed_tools')
    return {
        'guidance_revision':snapshot.get('guidance_revision',0),
        'instructions':[{key:row[key] for key in keys if key in row}
                        for row in snapshot.get('guidance',[])],
    }

class Development:
    # In-process ordering plus an OS-owned cross-process candidate writer lock.
    # Activation ownership remains separate from these source/test operations.
    _lock=threading.RLock()
    def __init__(self,store,root):
        self.store=store;self.workspaces=Workspaces(root)
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS development_candidates(id TEXT PRIMARY KEY,task_id TEXT NOT NULL,workspace TEXT NOT NULL)')

    def create(self,task):
        with self._lock:
            manifest=self.workspaces.create(task['workspace'])
            with self.store.connect() as db:
                db.execute('INSERT INTO development_candidates VALUES(?,?,?)',(manifest['id'],task['id'],str(Path(task['workspace']).resolve())))
            self.store.event(task['id'],'candidate_created',{'candidate_id':manifest['id'],'files':len(manifest['files']),'profile':manifest['profile']})
            return {**manifest,'candidate_path':str(self.workspaces.directory(manifest['id'],manifest))}

    def inspect(self,task,identifier):
        with self.store.connect() as db:row=db.execute('SELECT * FROM development_candidates WHERE id=?',(identifier,)).fetchone()
        same_owner=bool(row and row['task_id']==task['id'])
        if row and not same_owner:
            from ..conversation_memory import ConversationMemory
            memory=ConversationMemory(self.store)
            owner_chat=memory.chat_for_task(row['task_id'])
            same_owner=bool(owner_chat and owner_chat==memory.chat_for_task(task['id']))
        if not row or not same_owner or row['workspace']!=str(Path(task['workspace']).resolve()):
            raise ValueError('Candidate does not belong to this task and workspace')
        manifest=self.workspaces.inspect(identifier)
        evidence=[]
        for path in sorted(self.workspaces.candidate(identifier).glob('test-*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:10]:
            if path.is_symlink() or path.stat().st_size>2_000_000:continue
            record=json.loads(path.read_text(encoding='utf-8'))
            evidence.append({k:record.get(k) for k in ('revision','verified','exit_code','timed_out','source_changed')}|{'output':str(record.get('output',''))[:6000]})
        return {**manifest,'candidate_path':str(self.workspaces.directory(identifier,manifest)),'test_results':evidence}

    def list(self,task):
        with self.store.connect() as db:rows=db.execute('SELECT id FROM development_candidates WHERE task_id=?',(task['id'],)).fetchall()
        return {'task_id':task['id'],'candidates':[self.inspect(task,r['id']) for r in rows]}

    def read(self,task,identifier,paths,start=1,max_lines=80):
        from ..context.service import safe_path
        from .workspaces import sha
        if not 1<=len(paths)<=10:raise ValueError('Choose 1–10 source paths')
        if start<1 or not 1<=max_lines<=200:raise ValueError('Source start is 1-based; choose 1–200 lines')
        manifest=self.inspect(task,identifier);directory=self.workspaces.directory(identifier,manifest)
        files=[];total=0
        for rel in paths:
            if rel not in manifest['files']:raise ValueError('Path not found in candidate')
            data=safe_path(directory,rel).read_bytes();total+=len(data)
            if total>60000:raise ValueError('Source read exceeds 60 KB; narrow paths')
            if sha(data)!=manifest['files'][rel]:raise ValueError('Candidate hash changed')
            lines=data.decode('utf-8-sig').splitlines(keepends=True)
            if start>len(lines)+1:raise ValueError('Source start exceeds file length')
            selected=lines[start-1:start-1+max_lines];end=start+len(selected)-1
            files.append({'path':rel,'sha256':sha(data),'text':''.join(selected),'start':start,'end':end,'total_lines':len(lines),'next_line':end+1 if end<len(lines) else None})
        return {'candidate_id':identifier,'revision':manifest['revision'],'files':files}

    def patch(self,task,data):
        proposal=PatchProposal.model_validate(data)
        with self._lock:
            self.inspect(task,proposal.candidate_id)
            with candidate_owner(self.workspaces.candidate(proposal.candidate_id)):
                result=self.workspaces.propose(proposal.candidate_id,[c.model_dump() for c in proposal.changes],proposal.expected_revision)
            self.store.event(task['id'],'candidate_staged',{'candidate_id':result['id'],'revision':result['revision'],'paths':[c.path for c in proposal.changes]})
            return result

    def diff(self,task,identifier):
        with self._lock:
            self.inspect(task,identifier)
            return self.workspaces.diff(identifier)

    def stage_release(self,task,identifier,revision):
        from ..guardian import Guardian
        from ..config import ROOT
        manifest=self.inspect(task,identifier)
        with candidate_owner(self.workspaces.candidate(identifier)):
            manifest=self.inspect(task,identifier)
            if manifest['revision']!=revision:raise ValueError('Candidate revision conflict')
            evidence=next((r for r in manifest['test_results'] if r['revision']==revision and r['verified']),None)
            if not evidence:raise ValueError('Current candidate revision has no verified test evidence')
            if not self.workspaces.diff(identifier)['files']:raise ValueError('Candidate contains no source changes; complete the requested repair before staging an update')
            required={'hub/development/worker.py','hub/guardian/service.py','hub/__init__.py','requirements.lock.txt','pyproject.toml'}
            if not required.issubset(manifest['files']):raise ValueError('A complete Hub release candidate is required')
            result=Guardian(ROOT).stage(self.workspaces.directory(identifier,manifest),manifest['files'],evidence)
            self.store.event(task['id'],'worker_release_staged',{'candidate_id':identifier,'revision':revision,'release_id':result['id'],'activated':False})
            return {k:v for k,v in result.items() if k!='files'}|{'file_count':len(result['files'])}

    async def test(self,task,identifier,revision,tests,timeout=120):
        self.inspect(task,identifier)
        with candidate_owner(self.workspaces.candidate(identifier)):
            return await self._test_owned(task,identifier,revision,tests,timeout)

    async def _test_owned(self,task,identifier,revision,tests,timeout=120):
        from .runner import run_pytest
        from .workspaces import sha
        from ..context.service import safe_path
        with self._lock:
            manifest=self.inspect(task,identifier)
            if manifest['revision']!=revision:raise ValueError('Candidate revision conflict')
            directory=self.workspaces.directory(identifier,manifest)
            for rel,expected in manifest['files'].items():
                if sha(safe_path(directory,rel).read_bytes())!=expected:raise ValueError('Candidate content changed: '+rel)
            for selected in tests:
                rel=selected.split('::')[0]
                original=manifest.get('base_files',{}).get(rel)
                if original and manifest['files'].get(rel)!=original:
                    raise ValueError('Existing acceptance test was changed; cannot certify original test: '+rel)
        from .syntax import python_errors
        errors=python_errors({rel:safe_path(directory,rel).read_bytes() for rel in manifest['files'] if rel.endswith('.py')})
        result=({'exit_code':1,'output':'Python syntax preflight failed: '+json.dumps(errors),'timed_out':False,'truncated':False,'syntax_errors':errors}
                if errors else await run_pytest(directory,tests,timeout))
        result.update(candidate_id=identifier,revision=revision)
        with self._lock:
            current=self.inspect(task,identifier)
            changed=[rel for rel,h in manifest['files'].items() if not safe_path(directory,rel).is_file() or sha(safe_path(directory,rel).read_bytes())!=h]
            result.update(source_changed=changed,current_revision=current['revision'],verified=result['exit_code']==0 and not result['timed_out'] and not changed and current['revision']==revision)
            evidence=self.workspaces.candidate(identifier)/('test-'+__import__('uuid').uuid4().hex+'.json')
            evidence.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            self.store.event(task['id'],'candidate_tested',{'candidate_id':identifier,'revision':revision,'verified':result['verified'],'evidence':str(evidence)})
            result['evidence']=str(evidence)
            return result

    async def repair(self,task,identifier,revision,paths,tests,model=None,max_attempts=1):
        """Optional local test-feedback loop; never activates or approves its own patch."""
        if isinstance(max_attempts,bool) or not isinstance(max_attempts,int) or not 1<=max_attempts<=3:
            raise ValueError('Choose 1..3 repair attempts')
        from .guidance import Guidance
        baseline=self.store.get(task['id'])
        directive=Guidance(self.store).status(task['id'])
        attempts=[];feedback=None;seen=set()
        for number in range(1,max_attempts+1):
            current=self.store.get(task['id'])
            if current['state'] in ('paused','cancelled') or current['revision']!=baseline['revision'] or Guidance(self.store).status(task['id'])!=directive:
                raise ValueError('Task or director guidance changed; repair loop stopped')
            manifest=self.inspect(task,identifier)
            signature=tuple((p,manifest['files'].get(p)) for p in sorted(paths))
            if signature in seen:
                result.update(attempts=attempts,stop_reason='repeated_source_state')
                return result
            seen.add(signature)
            result=await self._repair_once(task,identifier,revision,paths,tests,model,feedback)
            evidence=result['test']
            attempts.append({'attempt':number,'revision':result['revision'],'verified':evidence['verified'],'evidence':evidence.get('evidence')})
            result.update(attempts=list(attempts),stop_reason='tests_passed' if evidence['verified'] else 'attempt_limit')
            if evidence['verified']:return result
            if evidence.get('timed_out') or evidence.get('source_changed'):
                result['stop_reason']='uncertain_test_effects';return result
            revision=result['revision']
            feedback={'previous_attempt':number,'exit_code':evidence.get('exit_code'),
                      'output':str(evidence.get('output',''))[-8000:],
                      'instruction':'The prior patch failed these tests. Diagnose the observed failure and correct the current permitted source. Preserve the original goal and read-only tests. Do not repeat the same patch.'}
            if number<max_attempts:
                self.store.event(task['id'],'coding_worker_test_feedback',{'candidate_id':identifier,'revision':revision,'next_attempt':number+1,'evidence':evidence.get('evidence')})
        return result

    async def _repair_once(self,task,identifier,revision,paths,tests,model=None,test_feedback=None):
        from .worker_runner import run
        from .worker import WorkerPatch
        from .workspaces import sha
        from ..context.service import safe_path
        from ..context.api import service_for_task
        from ..model_settings import load_settings
        task=self.store.get(task['id'])
        settings=load_settings();manifest=self.inspect(task,identifier)
        if not 1<=len(tests)<=30:raise ValueError('Choose 1–30 acceptance tests')
        if not 1<=len(paths)<=10 or len(set(paths))!=len(paths):raise ValueError('Choose 1–10 distinct permitted source paths')
        protected={p.split('::')[0] for p in tests}
        if protected.intersection(paths):raise ValueError('Acceptance tests are read-only to the coding worker')
        with candidate_owner(self.workspaces.candidate(identifier)):
            manifest=self.inspect(task,identifier)
            if manifest['revision']!=revision:raise ValueError('Candidate revision conflict')
            directory=self.workspaces.directory(identifier,manifest);sources={};total=0
            for rel in set(paths)|protected:
                data=safe_path(directory,rel).read_bytes();total+=len(data)
                if total>60000:raise ValueError('Worker source packet exceeds 60 KB; narrow scope')
                if sha(data)!=manifest['files'].get(rel):raise ValueError('Candidate source hash changed: '+rel)
                sources[rel]={'sha256':sha(data),'text':data.decode('utf-8-sig'),'writable':rel in paths}
            context,project_id=service_for_task(task,self.store)
            from .guidance import Guidance
            guidance_snapshot=Guidance(self.store).status(task['id'])
            command_event=self.store.latest_event(task['id'],'director_exact_command')
            director_correction=({key:command_event['data'].get(key) for key in ('request_id','reason')}
                                 if command_event and command_event['data'].get('reason') else None)
            packet={'schema':'mellow.worker-packet.v1','task_id':task['id'],'human_request_original':task['goal'],
                    'task_revision':task['revision'],'candidate_id':identifier,'candidate_revision':revision,
                    'model':model or settings.coding_model or settings.model,'allowed_paths':paths,'sources':sources,
                    'acceptance_tests':tests,'constraints':context.overview(project_id)['required_constraints'],
                    'guidance':worker_guidance(guidance_snapshot),'activation_requested':False,
                    'test_feedback':test_feedback,'director_correction':director_correction}
            packet_path=self.workspaces.candidate(identifier)/('worker-packet-'+__import__('uuid').uuid4().hex+'.json')
            packet_path.write_text(json.dumps(packet,ensure_ascii=False,indent=2),encoding='utf-8')
            self.store.event(task['id'],'coding_worker_started',{'candidate_id':identifier,'revision':revision,'packet':str(packet_path),'model':packet['model']})
            # Reject syntactically broken Python before touching the candidate.
            # Give the patch-only worker one bounded correction opportunity with
            # the actual parser error; do not ask the executor to rediscover it.
            for attempt in range(2):
                response=await run(packet,settings.request_timeout_seconds+15)
                proposed=WorkerPatch.model_validate(response['proposal'])
                syntax_errors=[]
                for change in proposed.changes:
                    if change.path not in paths:raise ValueError('Worker proposed a path outside its authorized scope')
                    if change.path.lower().endswith('.py'):
                        try:compile(change.content,change.path,'exec')
                        except SyntaxError as exc:syntax_errors.append({'path':change.path,'line':exc.lineno,'message':exc.msg})
                if not syntax_errors:break
                self.store.event(task['id'],'coding_worker_rejected',{'candidate_id':identifier,'attempt':attempt+1,'syntax_errors':syntax_errors,'candidate_changed':False})
                if attempt==1:raise ValueError('Coding worker returned invalid Python twice; candidate was not changed: '+json.dumps(syntax_errors))
                packet['correction_feedback']={'parser_errors':syntax_errors,'instruction':'Your previous proposal failed Python parsing and was not applied. Regenerate the requested small change from the original sources, with valid syntax and all unrelated source preserved. Return full corrected contents for permitted paths only.'}
                current_task=self.store.get(task['id'])
                if current_task['revision']!=packet['task_revision'] or Guidance(self.store).status(task['id'])!=guidance_snapshot:
                    raise ValueError('Task or director guidance changed; correction was not requested')
            current_task=self.store.get(task['id']);current_guidance=Guidance(self.store).status(task['id'])
            if current_task['revision']!=packet['task_revision'] or current_guidance!=guidance_snapshot:
                raise ValueError('Task or director guidance changed while worker ran; proposal was not applied. Rebuild the work packet.')
            proposal=WorkerPatch.model_validate(response['proposal'])
            if any(c.path not in paths for c in proposal.changes):raise ValueError('Worker proposed a path outside its authorized scope')
            if all(c.content==sources[c.path]['text'] for c in proposal.changes):
                self.store.event(task['id'],'coding_worker_rejected',{'candidate_id':identifier,'reason':'unchanged_source','candidate_changed':False})
                raise ValueError('Coding worker returned unchanged source; no repair was applied and candidate revision is unchanged. Review the failed tests and provide a focused correction.')
            changed=self.workspaces.propose(identifier,[{'path':c.path,'base_hash':sources[c.path]['sha256'],'content':c.content} for c in proposal.changes],revision)
            self.store.event(task['id'],'candidate_staged',{'candidate_id':identifier,'revision':changed['revision'],'origin':'coding_worker'})
            evidence=await self._test_owned(task,identifier,changed['revision'],tests)
            result={'candidate_id':identifier,'revision':changed['revision'],'test':evidence,'diff':self.workspaces.diff(identifier),'worker':{k:v for k,v in response.items() if k!='proposal'},'packet':str(packet_path),'activated':False}
            self.store.event(task['id'],'coding_worker_finished',{'candidate_id':identifier,'revision':changed['revision'],'verified':evidence['verified']})
            return result
