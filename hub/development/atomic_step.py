"""Atomic, audited SelfDevelop task and first guidance creation."""
import json
import uuid

from ..store import Conflict, now
from .guidance import Guidance


def _required_action(state):
    return {
        'failed': 'selfdevelop_close_failed with the current revision after inspecting evidence',
        'waiting_review': 'selfdevelop_review with the current revision',
        'waiting_user': 'inspect and correct the existing task',
        'queued': 'wait for execution, or stop_task if obsolete',
        'running': 'wait or use stop_task and verify termination',
        'verifying': 'wait for verification',
        'waiting_desktop': 'complete or safely cancel pending desktop action',
        'paused': 'inspect pause and reconcile or cancel safely',
    }.get(state, 'inspect and reconcile existing task before resubmitting')


def _blocker_error(row, reason=None):
    data = {
        'code': 'selfdevelop_blocked',
        'blocking_task_id': row['id'],
        'state': row['state'],
        'revision': row['revision'],
        'reason': reason or 'Prior SelfDevelop task is not terminal',
        'required_action': _required_action(row['state']),
    }
    return Conflict(json.dumps(data, ensure_ascii=False, sort_keys=True))


def submit_atomic_step(store, chat_id, request_id, instruction, allowed_tools,
                       required_tools=None, required_sources=None, evidence_only=False,
                       exact_patch=None, context_read=None):
    # No task row is created until all guidance is validated.
    if not allowed_tools:
        raise ValueError('Director must provide explicit allowed tools')
    guidance = Guidance(store)
    guide = guidance.validate_request(request_id, instruction, required_tools,
                                      required_sources, allowed_tools, evidence_only,
                                      exact_patch, context_read)
    if not guide['allowed_tools']:
        raise ValueError('Director must provide nonempty validated tool scope')
    idem = 'chat:' + chat_id + ':' + request_id
    task_id = None
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        chat = db.execute('''
            SELECT c.id,c.project_id,p.path AS workspace FROM chats c
            JOIN projects p ON p.id=c.project_id WHERE c.id=?''',
            (chat_id,)).fetchone()
        session = db.execute('SELECT chat_id FROM selfdevelop_sessions WHERE chat_id=?',
                             (chat_id,)).fetchone()
        if not chat or not session:
            raise Conflict('SelfDevelop chat/session not found')
        old = db.execute('SELECT * FROM tasks WHERE idem=?', (idem,)).fetchone()
        if old:
            task_id = old['id']
            owner = db.execute('SELECT 1 FROM chat_tasks WHERE task_id=? AND chat_id=?',
                               (task_id, chat_id)).fetchone()
            saved = db.execute('SELECT * FROM development_guidance WHERE task_id=? AND request_id=?',
                               (task_id, request_id)).fetchone()
            if old['goal'] != instruction or old['mode'] != 'code' or not owner:
                raise Conflict('Request identity belongs to a different task')
            if not saved:
                raise _blocker_error(old, 'Existing task lacks committed initial guidance; inspect and cancel/reconcile; never replay')
            same = (saved['text'] == instruction and
                    json.loads(saved['required_tools']) == guide['required_tools'] and
                    json.loads(saved['required_sources']) == guide['required_sources'] and
                    json.loads(saved['allowed_tools']) == guide['allowed_tools'] and
                    bool(saved['evidence_only']) == guide['evidence_only'] and
                    json.loads(saved['exact_patch']) == guide['exact_patch'] and
                    json.loads(saved['context_read']) == guide['context_read'])
            if not same:
                raise Conflict('Guidance request identity reused with different content')
        else:
            # CAS preflight is held under the same write lock as task/guidance commit.
            blocker = db.execute('''
                SELECT t.id,t.state,t.revision FROM chat_tasks c
                JOIN tasks t ON t.id=c.task_id
                WHERE c.chat_id=? AND t.state NOT IN ('done','cancelled')
                ORDER BY c.position DESC LIMIT 1''', (chat_id,)).fetchone()
            if blocker:
                raise _blocker_error(blocker)
            pending = db.execute('''
                SELECT t.id,t.state,t.revision FROM chat_tasks c
                JOIN tasks t ON t.id=c.task_id JOIN actions a ON a.task_id=t.id
                WHERE c.chat_id=? AND a.state='pending' LIMIT 1''',
                (chat_id,)).fetchone()
            if pending:
                raise _blocker_error(pending, 'Uncertain action must be reconciled with owner consent; no automatic replay')

            context = []
            note = db.execute('SELECT notes FROM project_notes WHERE project_id=?',
                              (chat['project_id'],)).fetchone()
            if note and note[0]:
                context.append({'role': 'user', 'content': 'User-saved project instructions: ' + note[0]})
            recent = [dict(r) for r in db.execute('''
                SELECT t.id,t.goal,t.result,t.state FROM chat_tasks c
                JOIN tasks t ON t.id=c.task_id WHERE c.chat_id=?
                ORDER BY c.position DESC LIMIT 12''', (chat_id,))][::-1]
            for task in recent:
                context.extend([
                    {'role': 'user', 'content': task['goal']},
                    {'role': 'assistant', 'content':
                     'Historical assistant report (not verified current state; may contain errors). '
                     'Use the original request and recorded evidence. ' +
                     json.dumps({'source_task_id': task['id'], 'state': task['state'],
                                 'reported_text': task['result'] or None}, ensure_ascii=False)},
                ])
                for event in db.execute("SELECT data FROM events WHERE task_id=? AND kind='attachments'",
                                        (task['id'],)):
                    context.append({'role':'user','content':'Previously attached files (data): ' + event['data']})
            context.append({'role': 'user', 'content': instruction})
            task_id = uuid.uuid4().hex
            stamp = now()
            db.execute('''
                INSERT INTO tasks(id,idem,revision,state,created,updated,goal,workspace,mode,messages)
                VALUES(?,?,2,'queued',?,?,?,?,?,?)''',
                (task_id,idem,stamp,stamp,instruction,chat['workspace'],'code',
                 json.dumps(context,ensure_ascii=False)))
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,1,?,?,?)',
                       (task_id,'created',json.dumps({'goal':instruction},ensure_ascii=False),stamp))
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,2,?,?,?)',
                       (task_id,'state','{}',stamp))
            pos = db.execute('SELECT COALESCE(MAX(position),-1)+1 FROM chat_tasks WHERE chat_id=?',
                             (chat_id,)).fetchone()[0]
            db.execute('INSERT INTO chat_tasks VALUES(?,?,?)', (chat_id,task_id,pos))
            if pos == 0:
                db.execute('UPDATE chats SET title=? WHERE id=?',(instruction[:70],chat_id))
            db.execute('''
                INSERT INTO development_guidance(
                    task_id,revision,request_id,text,epoch,created,required_tools,
                    required_sources,allowed_tools,evidence_only,exact_patch,context_read
                ) VALUES(?,1,?,?,'',?,?,?,?,?,?,?)''',
                (task_id,request_id,instruction,stamp,
                 json.dumps(guide['required_tools']),json.dumps(guide['required_sources']),
                 json.dumps(guide['allowed_tools']),int(guide['evidence_only']),
                 json.dumps(guide['exact_patch']),json.dumps(guide['context_read'])))
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,2,?,?,?)',
                       (task_id,'guidance_received',
                        json.dumps({'guidance_revision':1,'request_id':request_id,'consumer_epoch':''}),stamp))
            db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,2,?,?,?)',
                       (task_id,'selfdevelop_atomic_create',
                        json.dumps({'request_id':request_id,'guidance_revision':1}),stamp))
    return store.get(task_id)
