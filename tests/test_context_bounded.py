
import copy,json,hashlib
import pytest
from hub.store import Store,Conflict
from hub.conversations import Conversations
from hub.conversation_memory import ConversationMemory
from hub.model_context import build_packet,ContextBudgetError

def setup(tmp_path):
    store=Store(tmp_path/'state.sqlite3');chats=Conversations(store)
    project=chats.project(str(tmp_path));chat=chats.create(project['id'])
    return store,chats,chat['id'],ConversationMemory(store)

def test_protect_correction_current_image_and_complete_tool_group():
    messages=[{'role':'system','content':'Rules'},{'role':'user','content':'Objective'}]
    for i in range(30):
        messages.extend([{'role':'assistant','tool_calls':[{'function':{'name':'read_file','arguments':{'path':'x'}}}]},{'role':'tool','tool_name':'read_file','content':json.dumps({'text':'old '*2000})}])
    correction='CORRECTION '+'keep '*1000
    messages.insert(12,{'role':'user','content':correction})
    messages.append({'role':'user','content':'Current observation','images':['current-image']})
    original=copy.deepcopy(messages)
    packet,diag=build_packet(messages,[],16384,512,target_tokens=8000,task_id='task')
    assert messages==original
    assert any(m.get('content')==correction for m in packet)
    assert [m['images'] for m in packet if m.get('images')]==[['current-image']]
    for i,m in enumerate(packet):
        if m['role']=='tool':assert packet[i-1].get('tool_calls')
    assert diag['accounting']=='estimated' and diag['estimated_input']<=diag['input_budget']
    assert diag['omitted_message_count']>0
    with pytest.raises(ContextBudgetError):build_packet([{'role':'system','content':'x'*30000},{'role':'user','content':'required'}],[],2048,512)

def test_projection_restart_pending_cancellation_and_event_forgetting(tmp_path):
    store,chats,chat,memory=setup(tmp_path);task=chats.submit(chat,'Inspect only','inspect','one')
    action=store.begin_action(task['id'],'read_file',{'path':'missing'})
    result={'error':'FILE_NOT_FOUND exact-code'};store.end_action(action,result)
    store.event(task['id'],'tool_result',{'action_id':action,'name':'read_file','result':result})
    pending=store.begin_action(task['id'],'write_file',{'path':'uncertain'})
    first=memory.working_state(task['id'],task['revision'])
    assert first['failed_attempts'][0]['action_id']==action
    assert first['pending_operations'][0]['id']==pending
    second=ConversationMemory(Store(store.path)).working_state(task['id'],task['revision'])
    assert second['observations']==first['observations']
    assert len(store.actions(task['id']))==2
    store.update(task['id'],state='cancelled')
    with pytest.raises(Conflict):memory.working_state(task['id'],task['revision'])
    assert memory.working_state(task['id'])['lifecycle']=='cancelled'
    with store.connect() as db:
        db.execute("DELETE FROM events WHERE task_id=? AND kind='tool_result'",(task['id'],))
    assert memory.working_state(task['id'])['failed_attempts']==[]

def test_explicit_project_memory_private_scope_correction_and_source_change(tmp_path):
    store,chats,chat,memory=setup(tmp_path)
    first=chats.submit(chat,'Use BLUE for the project','inspect','one')
    a=memory.remember(chat,first['id'],'Use BLUE for the project','colour')
    store.update(first['id'],state='done')
    peer=chats.create(chats.get(chat)['project_id'])['id']
    (tmp_path/'other').mkdir()
    other=chats.create(chats.project(str(tmp_path/'other'))['id'])['id']
    memory.pin_memory(chat,a['id'],'chat',True,0)
    assert not memory.pinned_memory(peer)['items']
    memory.pin_memory(chat,a['id'],'project',True,1)
    assert memory.pinned_memory(peer)['items'][0]['quote']=='Use BLUE for the project'
    assert not memory.pinned_memory(other)['items']
    with pytest.raises(KeyError):memory.pin_memory(peer,a['id'],'project',True,2)
    correction=chats.submit(chat,'Use GREEN instead','inspect','two')
    memory.remember(chat,correction['id'],'Use GREEN instead','colour',a['id'])
    assert not memory.pinned_memory(peer)['items']
    with store.connect() as db:db.execute('DELETE FROM tasks WHERE id=?',(first['id'],))
    assert not memory.pinned_memory(peer)['items']

def test_original_evidence_cursor_scope_and_stale_hash(tmp_path):
    store,chats,chat,memory=setup(tmp_path);task=chats.submit(chat,'Read','inspect','one')
    text='original '+('x'*7000);messages=[{'role':'tool','content':text}]
    store.update(task['id'],messages=messages)
    digest=hashlib.sha256(text.encode()).hexdigest()
    page=memory.context_evidence(chat,task['id'],0,digest,0,3000)
    assert page['next_offset']==3000 and page['text']==text[:3000]
    other=chats.create(chats.get(chat)['project_id'])['id']
    with pytest.raises(KeyError):memory.context_evidence(other,task['id'],0,digest)
    store.update(task['id'],messages=[{'role':'tool','content':'changed'}])
    with pytest.raises(Conflict):memory.context_evidence(chat,task['id'],0,digest)
