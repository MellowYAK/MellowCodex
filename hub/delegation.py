"""Durable director/worker proposals. Workers cannot mutate the project.

Provider metadata is attributed to OmniRoute; orchestration is native Hub code.
External MCP/PLAY directors use the same revision-checked queue as the UI.
"""
import json
import uuid
import os
import time
from urllib.parse import urlsplit
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal
from .store import Conflict, now
from .conversations import Conversations


class Profile(BaseModel):
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    provider: str
    name: str = Field(min_length=1, max_length=100)
    model: str = Field(default='', max_length=200)
    transport: Literal['mcp', 'play', 'api'] = 'mcp'
    endpoint: str = ''
    key_env: str = Field(default='',pattern=r'^[A-Za-z_][A-Za-z0-9_]*$|^$')


class Delegation:
    def __init__(self, store):
        self.store = store
        from .bridge_transcript import BridgeTranscript
        BridgeTranscript(store)
        with store.connect() as db:
            db.executescript('''
CREATE TABLE IF NOT EXISTS delegation_profiles(id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS delegation_runs(id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, chat_id TEXT NOT NULL, data TEXT NOT NULL, revision INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS delegation_events(seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, at TEXT NOT NULL, data TEXT NOT NULL);
''')

    def catalog(self):
        data = json.loads((Path(__file__).parent/'provider_catalog.json').read_text(encoding='utf-8'))
        return {'providers': data['providers'], 'source': data['source'], 'commit': data['commit'],
                'transports': ['mcp', 'play', 'api'], 'execution': 'external_director',
                'note': 'Catalog entries are not authenticated connections. MCP clients must connect to the Hub; PLAY requires a working provider browser adapter. API workers require an explicitly configured OpenAI-compatible chat-completions endpoint. The director is an external client; no automatic director API planner is implied.'}

    def profiles(self):
        with self.store.connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT data FROM delegation_profiles ORDER BY id')]

    def save_profile(self, profile):
        p = Profile.model_validate(profile).model_dump()
        if p['transport']=='api':
            url=urlsplit(p['endpoint'])
            if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError('Use an API base URL without credentials or query parameters')
            if url.scheme=='http' and url.hostname not in ('localhost','127.0.0.1','::1'):
                raise ValueError('Remote API endpoints require HTTPS')
            if not p['model'].strip():raise ValueError('API profiles require a model')
        if p['provider'] not in {x['id'] for x in self.catalog()['providers']} | {'chatgpt','claude','deepseek','custom'}:
            raise ValueError('Unknown provider')
        p['connection_state'] = 'not_verified'
        p['delivery'] = 'existing_chatgpt_adapter' if p['provider']=='chatgpt' and p['transport']=='play' else ('openai_compatible_api' if p['transport']=='api' else 'external_client')
        with self.store.connect() as db:
            db.execute('INSERT OR REPLACE INTO delegation_profiles VALUES(?,?)',(p['id'],json.dumps(p)))
        return {**p, 'effective':'new_runs', 'restart_required':False}

    def start(self, chat_id, request_id, objective, director_id):
        Conversations(self.store).get(chat_id)
        profiles = {p['id']:p for p in self.profiles()}
        if director_id not in profiles: raise ValueError('Configure the director profile first')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM delegation_runs WHERE request_id=?',(request_id,)).fetchone()
            if row:
                old=json.loads(row['data'])
                if (row['chat_id'],old['objective'],old['director']['id']) != (chat_id,objective,director_id):
                    raise Conflict('Request ID already used for another objective')
                return {**old,'revision':row['revision']}
            run={'id':uuid.uuid4().hex,'chat_id':chat_id,'objective':objective,'director':profiles[director_id],
                 'state':'waiting_director','workers':[],'created':now(),'execution_task_id':None}
            db.execute('INSERT INTO delegation_runs VALUES(?,?,?,?,0)',(run['id'],request_id,chat_id,json.dumps(run)))
            self._event(db,run,'created')
        return {**run,'revision':0}

    def _event(self, db, run, action):
        db.execute('INSERT INTO delegation_events(run_id,at,data) VALUES(?,?,?)',(run['id'],now(),json.dumps({'action':action,'state':run['state']})))
        from .i18n import t
        text=t('delegation.title','he')+': '+run['objective']+'\n'+t('delegation.'+run['state'],'he')
        db.execute('INSERT INTO bridge_messages VALUES(?,?,?,?,?,?,?,?,?)',
            (uuid.uuid4().hex,run['chat_id'],None,'agent','local',text,'[]',run['state'],time.time()))

    def status(self, run_id):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM delegation_runs WHERE id=?',(run_id,)).fetchone()
            if not row: raise KeyError('Delegation not found')
            data=json.loads(row['data'])
            expired=False
            for worker in data['workers']:
                if worker['state']=='running' and worker.get('expires',0)<time.time():
                    worker.update(state='failed',result='Provider request expired or process restarted; explicit retry required')
                    expired=True
            if expired:
                data['state']='waiting_review'
                db.execute('UPDATE delegation_runs SET data=?,revision=revision+1 WHERE id=?',(json.dumps(data),run_id))
                self._event(db,data,'worker_expired')
                row=db.execute('SELECT * FROM delegation_runs WHERE id=?',(run_id,)).fetchone()
            events=[{'at':e[0],**json.loads(e[1])} for e in db.execute('SELECT at,data FROM delegation_events WHERE run_id=? ORDER BY seq',(run_id,))]
        run={**json.loads(row['data']),'revision':row['revision'],'events':events}
        if run['execution_task_id']:
            task=self.store.get(run['execution_task_id'])
            run['execution']={k:task[k] for k in ('id','state','revision','result')}
        return run

    def list(self, chat_id):
        with self.store.connect() as db:
            ids=[r[0] for r in db.execute('SELECT id FROM delegation_runs WHERE chat_id=? ORDER BY rowid DESC',(chat_id,))]
        return [self.status(i) for i in ids]

    def guard(self, task_id):
        task=self.store.get(task_id)
        if ':delegation:' not in task.get('idem',''):return
        run_id=task['idem'].rsplit(':delegation:',1)[1]
        run=self.status(run_id)
        if run['state']!='waiting_execution_review' or run['execution_task_id']!=task_id:
            raise Conflict('Delegation dispatch is incomplete; inspect before resuming')
        from .development.guidance import Guidance
        guide=Guidance(self.store)
        if not guide.allowed_tools(task_id) or not (guide.exact_patch(task_id) or guide.context_read(task_id)):
            raise Conflict('Delegation requires exact director instructions before execution')

    def update(self, run_id, revision, action, payload):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM delegation_runs WHERE id=?',(run_id,)).fetchone()
            if not row:raise KeyError('Delegation not found')
            if row['revision']!=revision:raise Conflict('Stale delegation revision; read status before retrying')
            run=json.loads(row['data'])
            if run['state'] in ('completed','cancelled'):raise Conflict('Delegation is terminal')
            if action=='assign':
                if run['state'] not in ('waiting_director','working','waiting_review'):raise Conflict('Execution already dispatched')
                configured={p['id']:p for p in self.profiles()}
                worker_id=payload['worker']['id']
                if worker_id not in configured:raise ValueError('Save the worker profile first')
                p=configured[worker_id]
                instruction=payload['instruction'].strip()
                if not instruction:raise ValueError('A bounded worker instruction is required')
                if len(run['workers'])>=32:raise ValueError('Split large plans into separate reviewed runs')
                dependencies=payload.get('dependencies',[])
                if any(x not in {w['id'] for w in run['workers']} for x in dependencies):raise ValueError('Unknown dependency')
                run['workers'].append({'id':uuid.uuid4().hex,'profile':p,'instruction':instruction,
                    'dependencies':dependencies,'state':'assigned','result':'','feedback':''})
                run['state']='working'
            elif action in ('result','review','retry'):
                worker=next((w for w in run['workers'] if w['id']==payload['worker_id']),None)
                if not worker:raise KeyError('Worker not found')
                if action=='retry':
                    if worker['state'] not in ('failed','running'):raise Conflict('Only failed or interrupted workers can be retried')
                    if worker['state']=='running':raise Conflict('A running batch cannot be replayed; inspect the pending provider request first')
                    worker.update(state='changes_requested',feedback=payload.get('feedback','Retry after provider configuration was corrected'))
                elif action=='result':
                    if worker['state'] not in ('assigned','changes_requested'):raise Conflict('Worker is not awaiting a result')
                    if any(w['state']!='approved' for w in run['workers'] if w['id'] in worker['dependencies']):raise Conflict('Dependencies require director approval first')
                    result=payload['result'].strip()
                    if not result:raise ValueError('Observed worker output is required')
                    worker.update(result=result,state='waiting_review')
                else:
                    if worker['state']!='waiting_review':raise Conflict('Worker has no result to review')
                    if payload['decision'] not in ('approved','changes_requested','rejected'):raise ValueError('Invalid review decision')
                    if not payload.get('feedback','').strip():raise ValueError('Director review rationale is required')
                    worker.update(state=payload['decision'],feedback=payload['feedback'])
                run['state']='ready_for_execution' if all(w['state']=='approved' for w in run['workers']) else 'waiting_review'
            elif action=='cancel':
                if run['execution_task_id']:raise Conflict('Stop the execution task first; cancellation is not an execution stop')
                run['state']='cancelled'
            elif action=='complete':
                if not run['execution_task_id']:raise Conflict('No execution result to approve')
                task=db.execute('SELECT state FROM tasks WHERE id=?',(run['execution_task_id'],)).fetchone()
                if not task or task[0]!='done':raise Conflict('Review and approve the local execution task first')
                run['state']='completed'
            else:raise ValueError('Unknown delegation action')
            db.execute('UPDATE delegation_runs SET data=?,revision=revision+1 WHERE id=?',(json.dumps(run),run_id))
            self._event(db,run,action)
        return self.status(run_id)

    async def run_workers(self, run_id):
        """Run eligible API proposals in parallel; never tools or project writes."""
        import asyncio
        import httpx
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT data FROM delegation_runs WHERE id=?',(run_id,)).fetchone()
            if not row:raise KeyError('Delegation not found')
            run=json.loads(row[0])
            if run['state'] in ('completed','cancelled','dispatching','waiting_execution_review'):raise Conflict('Run is not accepting workers')
            if any(w['state']=='running' for w in run['workers']):raise Conflict('Worker batch already running')
            approved={w['id'] for w in run['workers'] if w['state']=='approved'}
            eligible=[w for w in run['workers'] if w['state'] in ('assigned','changes_requested') and w['profile']['transport']=='api' and set(w['dependencies'])<=approved][:3]
            for w in eligible:w.update(state='running',attempt=uuid.uuid4().hex,expires=time.time()+150)
            run['state']='working' if eligible else run['state']
            db.execute('UPDATE delegation_runs SET data=?,revision=revision+1 WHERE id=?',(json.dumps(run),run_id))
            self._event(db,run,'api_batch_started')
        async def work(worker):
            p=worker['profile'];state='waiting_review'
            try:
                headers={}
                if p['key_env']:
                    key=os.environ.get(p['key_env'])
                    if not key:raise ValueError('Configured credential environment variable is unavailable')
                    headers['Authorization']='Bearer '+key
                dependencies=[{'id':w['id'],'result':w['result']} for w in run['workers'] if w['id'] in worker['dependencies']]
                async with httpx.AsyncClient(timeout=120,follow_redirects=False) as client:
                    response=await client.post(p['endpoint'].rstrip('/')+'/chat/completions',headers=headers,json={
                        'model':p['model'],'stream':False,'messages':[
                            {'role':'system','content':'You are a proposal-only worker. Follow your bounded assignment. Do not claim actions were executed. No tools are available. Return evidence, proposed changes and uncertainties for director review.'},
                            {'role':'user','content':json.dumps({'objective':run['objective'],'assignment':worker['instruction'],'feedback':worker['feedback'],'dependencies':dependencies},ensure_ascii=False)}]})
                if response.status_code!=200:raise ValueError('Provider HTTP '+str(response.status_code))
                result=response.json()['choices'][0]['message']['content']
                if not isinstance(result,str) or not result.strip():raise ValueError('Provider returned no textual proposal')
            except Exception as exc:
                state='failed'
                # Never persist response bodies, headers or credentials in errors.
                result=str(exc) if isinstance(exc,ValueError) else type(exc).__name__
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                current=json.loads(db.execute('SELECT data FROM delegation_runs WHERE id=?',(run_id,)).fetchone()[0])
                target=next(w for w in current['workers'] if w['id']==worker['id'])
                if current['state']=='cancelled' or target['state']!='running' or target.get('attempt')!=worker['attempt']:return
                target.update(state=state,result=result)
                current['state']='working' if any(w['state']=='running' for w in current['workers']) else 'waiting_review'
                db.execute('UPDATE delegation_runs SET data=?,revision=revision+1 WHERE id=?',(json.dumps(current),run_id))
                self._event(db,current,'worker_'+state)
        await asyncio.gather(*(work(w) for w in eligible))
        return self.status(run_id)

    def dispatch(self, run_id, revision, instruction, allowed_tools, exact_patch=None, context_read=None):
        """Deterministic operations only: no worker proposal executes automatically."""
        from .development.guidance import Guidance, ContextRead
        from .development.contracts import PatchProposal
        if bool(exact_patch)==bool(context_read):raise ValueError('Supply exactly one exact_patch or context_read')
        if context_read:ContextRead.model_validate(context_read)
        if exact_patch:PatchProposal.model_validate(exact_patch)
        if not allowed_tools:raise ValueError('Explicit tool scope required')
        run=self.status(run_id)
        if run['revision']!=revision:raise Conflict('Stale delegation revision')
        if run['execution_task_id']:return self.store.get(run['execution_task_id'])
        if run['state']!='ready_for_execution':raise Conflict('Director must approve all worker outputs first')
        # Claim before creating a task. An interrupted dispatch requires inspection;
        # it must never blindly replay a potentially applied patch.
        with self.store.connect() as db:
            changed=db.execute('UPDATE delegation_runs SET revision=revision+1,data=? WHERE id=? AND revision=?',
                (json.dumps({**run,'state':'dispatching'}),run_id,revision)).rowcount
            if not changed:raise Conflict('Concurrent dispatch')
        task=Conversations(self.store).submit(run['chat_id'],instruction,'code','delegation:'+run_id)
        guide=Guidance(self.store);state=guide.status(task['id'])
        guide.submit(task['id'],task['revision'],state['guidance_revision'],state['consumer_epoch'],
            'delegation:'+run_id,instruction,allowed_tools=allowed_tools,exact_patch=exact_patch,context_read=context_read)
        with self.store.connect() as db:
            run.update(state='waiting_execution_review',execution_task_id=task['id'])
            run.pop('events',None);run.pop('revision',None)
            db.execute('UPDATE delegation_runs SET data=?,revision=revision+1 WHERE id=?',(json.dumps(run),run_id))
            self._event(db,run,'dispatched')
        return task
