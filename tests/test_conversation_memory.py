import json
import pytest
from hub.store import Store,Conflict
from hub.conversations import Conversations
from hub.conversation_memory import ConversationMemory
from hub.model_context import compact_result


def setup_chat(tmp_path):
    store=Store(tmp_path/'history.sqlite3');chats=Conversations(store)
    project=chats.project(str(tmp_path));chat=chats.create(project['id'])
    return store,chats,chat['id']


def test_old_turn_exact_paging_restart_and_scoping(tmp_path):
    store,chats,chat=setup_chat(tmp_path)
    original='החלטה מקורית '+('טקסט ארוך '*1200)
    for index in range(25):
        task=chats.submit(chat,original if index==0 else f'Turn {index}','inspect',str(index))
        store.update(task['id'],state='done',result=f'Result {index}')
        if index==0:first=task['id']
    memory=ConversationMemory(Store(store.path));page=memory.history(chat,limit=4)
    assert page['total_turns']==25 and page['next_after']==3
    assert memory.history(chat,after=page['next_after'],limit=4)['turns'][0]['position']==4
    assert memory.history(chat,query='החלטה')['turns'][0]['id']==first
    fallback=memory.history(chat,query='translated phrase not present')
    assert fallback['chronological_fallback'] and fallback['turns'][0]['id']==first
    text='';offset=0
    while True:
        data=json.loads(compact_result(memory.history(chat,task_id=first,field='goal',offset=offset,chars=6000),1200))
        text+=data['text'];offset=data['next_offset']
        if offset is None:break
    assert text==original
    other=chats.create(chats.get(chat)['project_id'])
    with pytest.raises(KeyError):memory.history(other['id'],task_id=first)
    assert '25' in memory.packet(task['id'])


def test_notes_revision_conflict_clear_and_no_history_deletion(tmp_path):
    store,chats,chat=setup_chat(tmp_path);memory=ConversationMemory(store)
    assert memory.save_note(chat,'Preserve original tests',0,'director')['revision']==1
    with pytest.raises(Conflict):memory.save_note(chat,'stale',0)
    assert memory.save_note(chat,'',1)['revision']==2
    with store.connect() as db:
        assert db.execute('SELECT text FROM conversation_notes WHERE revision=1').fetchone()[0]=='Preserve original tests'
    assert ConversationMemory(Store(tmp_path/'standalone.sqlite3')).packet('unknown')==''


def test_submit_does_not_deserialize_old_turn_messages(tmp_path,monkeypatch):
    store,chats,chat=setup_chat(tmp_path);old=set()
    for index in range(30):
        task=chats.submit(chat,f'Historical {index}','inspect',str(index));old.add(task['id'])
        store.update(task['id'],state='done',result=f'Result {index}')
    original_get=store.get
    def guarded(task_id):
        assert task_id not in old,'Submitting a new turn must not materialize old task/message arrays'
        return original_get(task_id)
    monkeypatch.setattr(store,'get',guarded)
    task=chats.submit(chat,'Continue','inspect','next')
    assert task['messages'][-1]['content']=='Continue'
    assert len(task['messages'])==25


def test_ui_pages_retain_order_and_cursor_while_new_turns_arrive(tmp_path,monkeypatch):
    store,chats,chat=setup_chat(tmp_path)
    for index in range(65):
        task=chats.submit(chat,f'Turn {index}','inspect',str(index))
        store.update(task['id'],state='done',result=f'Result {index}')
    def no_full_task(_):raise AssertionError('Viewport must not load internal task messages')
    monkeypatch.setattr(store,'get',no_full_task)
    newest=chats.page(chat,limit=30)
    assert newest['turns'][0]['position']==35 and newest['next_before']==35
    assert 'messages' not in newest['turns'][0]
    previous=chats.page(chat,before=newest['next_before'],limit=30)
    oldest=chats.page(chat,before=previous['next_before'],limit=30)
    assert [t['position'] for t in oldest['turns']+previous['turns']+newest['turns']]==list(range(65))
    assert not oldest['has_older'] and oldest['next_before'] is None
    assert oldest['total_turns']==65
    with pytest.raises(ValueError):chats.page(chat,limit=10000)


def test_source_bound_decisions_keep_corrections_and_survive_restart(tmp_path):
    store,chats,chat=setup_chat(tmp_path);memory=ConversationMemory(store)
    first=chats.submit(chat,'Use SQLite and preserve every test','inspect','decision-one')
    store.update(first['id'],state='done',result='acknowledged')
    a=memory.remember(chat,first['id'],'Use SQLite','Database choice')
    with pytest.raises(ValueError):memory.remember(chat,first['id'],'Use Postgres','Invented quote')
    later=chats.submit(chat,'Correction: use Postgres instead of SQLite','inspect','decision-two')
    store.update(later['id'],state='done',result='acknowledged')
    b=memory.remember(chat,later['id'],'use Postgres instead of SQLite','Corrected database',a['id'])
    assert memory.remember(chat,later['id'],'use Postgres instead of SQLite','Corrected database',a['id'])['id']==b['id']
    restarted=ConversationMemory(Store(store.path))
    page=restarted.anchors(chat,limit=1)
    assert page['items'][0]['id']==b['id'] and page['next_after'] is not None
    old=restarted.anchors(chat,after=page['next_after'])['items'][0]
    assert old['id']==a['id'] and old['superseded']
    assert 'Postgres' in restarted.packet(later['id'])
    with pytest.raises(ValueError):memory.remember(chat,first['id'],'Use SQLite','Reverse correction',b['id'])
    # Simulate an external database edit: normal Store.update protects goals.
    with store.connect() as db:db.execute('UPDATE tasks SET goal=? WHERE id=?',('Edited source',later['id']))
    assert restarted.anchors(chat)['items'][0]['source_changed']


def test_compacted_anchor_pages_traverse_every_original_source(tmp_path):
    import json
    from hub.model_context import compact_result
    store,chats,chat=setup_chat(tmp_path);memory=ConversationMemory(store)
    expected=[]
    for i in range(7):
        quote=f'Decision {i}: '+('original evidence '*35)
        task=chats.submit(chat,quote,'inspect',f'page-{i}')
        store.update(task['id'],state='done',result='Recorded')
        expected.append(memory.remember(chat,task['id'],quote,f'Decision {i}')['id'])
    after=None;seen=[]
    for _ in range(10):
        page=json.loads(compact_result(memory.anchors(chat,after=after),1500))
        seen.extend(item['id'] for item in page['items'])
        after=page['next_after']
        if after is None:break
    assert seen==list(reversed(expected))


def test_relevant_decisions_keep_correction_chain_scope_and_changed_source(tmp_path):
    store,chats,chat=setup_chat(tmp_path);memory=ConversationMemory(store)
    task=chats.submit(chat,'שם סביבת הקבלה: תמר','inspect','original')
    store.update(task['id'],state='done',result='Recorded')
    first=memory.remember(chat,task['id'],'שם סביבת הקבלה: תמר','סביבת הקבלה')
    correction=chats.submit(chat,'תיקון: השם הוא הדס','inspect','correction')
    store.update(correction['id'],state='done',result='Recorded')
    second=memory.remember(chat,correction['id'],'תיקון: השם הוא הדס','עדכון',first['id'])
    page=memory.relevant_anchors(chat,'סביבת הקבלה',limit=1)
    assert {i['id'] for i in page['items']}=={first['id'],second['id']}
    other=chats.create(chats.get(chat)['project_id'])['id']
    assert not memory.relevant_anchors(other,'סביבת הקבלה')['items']
    assert not memory.relevant_anchors(chat,'" OR *')['items']
    with store.connect() as db:db.execute('UPDATE tasks SET goal=? WHERE id=?',('Externally changed',task['id']))
    reopened=ConversationMemory(Store(store.path))
    assert next(i for i in reopened.relevant_anchors(chat,'סביבת הקבלה')['items'] if i['id']==first['id'])['source_changed']


def test_anchor_index_migrates_existing_records(tmp_path):
    store,chats,chat=setup_chat(tmp_path);memory=ConversationMemory(store)
    task=chats.submit(chat,'Database choice SQLite','inspect','old')
    memory.remember(chat,task['id'],'Database choice SQLite','Database')
    with store.connect() as db:
        for trigger in ('anchor_search_insert','anchor_search_delete','anchor_search_update'):
            db.execute('DROP TRIGGER '+trigger)
        db.execute('DROP TABLE conversation_anchor_search')
    reopened=ConversationMemory(Store(store.path))
    assert reopened.relevant_anchors(chat,'Database')['items'][0]['source_task_id']==task['id']


def test_unanchored_token_candidates_page_without_exact_question_hiding_sources(tmp_path):
    store,chats,chat=setup_chat(tmp_path);memory=ConversationMemory(store)
    expected=[]
    for i,text in enumerate(['קוד סביבת הקבלה הוא תמר','תיקון קוד סביבת הקבלה הוא הדס','מה מזהה סביבת הקבלה?']):
        task=chats.submit(chat,text,'inspect',str(i));expected.append(task['id'])
        store.update(task['id'],state='done',result='Old assistant report')
    after=-1;seen=[]
    for _ in range(3):
        page=memory.history(chat,query='מזהה סביבת הקבלה',after=after,limit=1)
        seen.extend(t['id'] for t in page['turns'])
        assert not page['chronological_fallback']
        if page['turns'][0]['id']!=expected[-1]:
            assert page['search_mode']=='literal_and_token_candidates'
            assert page['turns'][0]['match_kind']=='token_candidate'
        after=page['next_after']
        if after is None:break
    assert seen==expected
    other=chats.create(chats.get(chat)['project_id'])['id']
    assert not memory.history(other,query='סביבת הקבלה')['turns']
    assert memory.anchors(chat)['items']==[]
    # Original request index tracks changes without a rebuild; stale text must
    # not match after removal from both the request and assistant report.
    with store.connect() as db:db.execute('UPDATE tasks SET goal=? WHERE id=?',('Unrelated source',expected[0]))
    ids=[t['id'] for t in memory.history(chat,query='סביבת הקבלה')['turns']]
    assert expected[0] not in ids
