"""One director-authored command, executed by the ordinary local runner."""
import json
from .selfdevelop import SelfDevelop
from ..store import Conflict, now

def dispatch(store,chat_id,request_id,instruction,command,shell='powershell',timeout=60):
    if shell not in ('powershell','cmd') or not isinstance(command,str) or not command.strip() or len(command)>20000:
        raise ValueError('Invalid exact command')
    if not isinstance(timeout,int) or isinstance(timeout,bool) or not 1<=timeout<=180:
        raise ValueError('Timeout must be 1..180 seconds')
    service=SelfDevelop(store)
    service.status(chat_id)
    args={'command':command,'shell':shell,'timeout':timeout}
    idem='chat:'+chat_id+':'+request_id
    with store.connect() as db:
        old=db.execute('SELECT id FROM tasks WHERE idem=?',(idem,)).fetchone()
    if old:
        task=store.get(old['id'])
        event=store.latest_event(task['id'],'director_exact_command')
        if not event or event['data']['arguments']!=args or task['goal']!=instruction:
            raise Conflict('Exact command request identity reused with different content')
        return task
    task=service.step(chat_id,request_id,instruction,['run_shell'],required_tools=['run_shell'])
    store.event(task['id'],'director_exact_command',{'arguments':args,'request_id':request_id})
    return store.get(task['id'])

def command_actions(store,task_id):
    event=store.latest_event(task_id,'director_exact_command')
    if not event:return None,[]
    # A command task has only one action. Include pending records so reconnect
    # never replays an uncertain side effect.
    baseline=set(event['data'].get('baseline_action_ids',[]))
    return event,[a for a in store.actions(task_id) if a['tool']=='run_shell' and a['id'] not in baseline]

def next_command(store,task_id):
    event,actions=command_actions(store,task_id)
    if not event:return None,False
    if actions:return None,True
    return {'role':'assistant','content':'Executing the director command.',
            'tool_calls':[{'function':{'name':'run_shell','arguments':event['data']['arguments']}}]},False

def command_receipt(store,task_id):
    event,actions=command_actions(store,task_id)
    successful=bool(event and len(actions)==1 and actions[0]['state']=='complete'
                    and actions[0]['args']==event['data']['arguments']
                    and actions[0].get('result',{}).get('exit_code')==0
                    and not actions[0].get('result',{}).get('error'))
    return {'status':'awaiting_director_review' if successful else 'command_requires_diagnosis',
            'execution_succeeded':successful,'semantic_verified':False,
            'model_inference':False,'actions':actions}

def correct(store,chat_id,task_id,expected_revision,request_id,reason,command,shell='powershell',timeout=60):
    """Queue an explicitly corrected command on the same stopped task."""
    if not isinstance(request_id,str) or not 8<=len(request_id)<=100 or not reason.strip() or len(reason)>8000:
        raise ValueError('Correction identity and reason are required')
    if shell not in ('powershell','cmd') or not isinstance(command,str) or not command.strip() or len(command)>20000:
        raise ValueError('Invalid corrected command')
    if not isinstance(timeout,int) or isinstance(timeout,bool) or not 1<=timeout<=180:
        raise ValueError('Invalid timeout')
    service=SelfDevelop(store)
    if service.status(chat_id)['task_id']!=task_id:
        raise Conflict('Correction must target the current step in this chat')
    service.guard(task_id)
    args={'command':command,'shell':shell,'timeout':timeout}
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        task=db.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
        events=db.execute("SELECT data FROM events WHERE task_id=? AND kind='director_exact_command' ORDER BY seq",(task_id,)).fetchall()
        if not events:raise Conflict('Task is not an exact command')
        for row in events:
            data=json.loads(row['data'])
            if data.get('request_id')==request_id:
                if data.get('arguments')!=args or data.get('reason')!=reason:
                    raise Conflict('Correction request identity reused')
                return store._decode(task)
        if task['revision']!=expected_revision or task['state'] not in ('waiting_user','waiting_review'):
            raise Conflict('Correction requires current stopped task revision')
        if db.execute("SELECT 1 FROM actions WHERE task_id=? AND state='pending'",(task_id,)).fetchone():
            raise Conflict('Reconcile uncertain actions before correcting')
        baseline=[r[0] for r in db.execute('SELECT id FROM actions WHERE task_id=?',(task_id,))]
        revision=task['revision']+1
        data={'arguments':args,'request_id':request_id,'reason':reason,'baseline_action_ids':baseline}
        db.execute("UPDATE tasks SET state='queued',revision=?,updated=?,result='' WHERE id=?",(revision,now(),task_id))
        db.execute('INSERT INTO events(task_id,revision,kind,data,at) VALUES(?,?,?,?,?)',(task_id,revision,'director_exact_command',json.dumps(data),now()))
    return store.get(task_id)