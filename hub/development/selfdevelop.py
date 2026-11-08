"""Persistent, director-controlled development sessions for the Hub itself.

This is an orchestration mode, not a control-plane deployment supervisor.
"""
from pathlib import Path
import json
from ..conversations import Conversations
from ..store import Conflict, now
from .guidance import Guidance


class SelfDevelop:
    def __init__(self, store):
        self.store = store
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS selfdevelop_sessions (chat_id TEXT PRIMARY KEY, objective TEXT NOT NULL, transport TEXT NOT NULL, created TEXT NOT NULL)')

    def start(self, objective, conversation_key, transport):
        if not objective.strip():
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

    def status(self, chat_id):
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM selfdevelop_sessions WHERE chat_id=?', (chat_id,)).fetchone()
        if not row:
            raise KeyError('SelfDevelop session not found')
        chat = Conversations(self.store).get(chat_id)
        last = chat['turns'][-1] if chat['turns'] else None
        return {**dict(row), 'mode': 'selfdevelop', 'director': 'external',
                'executor': 'local', 'state': last['state'] if last else 'waiting_director',
                'task_id': last['id'] if last else None,
                'task_revision': last['revision'] if last else None,
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
