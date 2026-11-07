import pytest
import json
from hub.store import Store,Conflict
from hub.conversations import Conversations
from hub.memory_review import MemoryReview


@pytest.mark.parametrize('status,verdict,expected',[
    ('reviewed','confirmed','אושר לפי ההקשר'),
    ('reviewed','contradicted','נמצאה סתירה'),
    ('reviewed','unavailable','לא ניתן לאמת'),
    ('pending',None,'ממתין למשוב'),
    ('stale','confirmed','המקור השתנה')])
def test_feedback_summary_preserves_recorded_status_and_provenance(status,verdict,expected):
    text=MemoryReview.summary({'status':status,'request':{'source_task_id':'source','claim':'Historical count','evidence_quote':'7'},
        'response':{'verdict':verdict,'transport':'browser','evidence':'Exact remote evidence'}})
    assert expected in text and 'source' in text and '7' in text
    assert ('Exact remote evidence' in text)==(status=='reviewed')
    assert 'לא בדיקה חדשה' in text


def test_browser_feedback_must_match_request_and_validate_payload():
    answer={'review_id':'current','memory_review':{'verdict':'confirmed','context_available':True,'evidence':'Original request visible'}}
    assert MemoryReview.parse_browser_reply('current',{'text':json.dumps(answer)})['verdict']=='confirmed'
    assert MemoryReview.parse_browser_reply('different',{'text':json.dumps(answer)})['verdict']=='unavailable'
    del answer['review_id']
    assert MemoryReview.parse_browser_reply('current',{'text':json.dumps(answer)})['verdict']=='unavailable'
    answer['review_id']='current';answer['memory_review']['context_available']='true'
    assert MemoryReview.parse_browser_reply('current',{'text':json.dumps(answer)})['verdict']=='unavailable'
    assert MemoryReview.parse_browser_reply('current',{'text':'[1,2,3]'})['verdict']=='unavailable'


def fixture(tmp_path):
    store=Store(tmp_path/'review.sqlite3');chats=Conversations(store)
    project=chats.project(str(tmp_path));chat=chats.create(project['id'])
    task=chats.submit(chat['id'],'Keep the original tests','inspect','first')
    store.update(task['id'],state='done',result='Saved project name: Cedar')
    return store,chats,chat['id'],task['id'],MemoryReview(store)


@pytest.mark.parametrize('invalid', ['false', 'true', 0, 1, None, [], {}])
def test_feedback_rejects_ambiguous_context_without_saving(tmp_path, invalid):
    store,chats,chat,task,review=fixture(tmp_path)
    review.settings(chat,True,'mcp')
    pending=review.request(chat,task,'Name is Cedar',evidence_quote='Cedar')
    with pytest.raises(ValueError,match='boolean'):
        review.respond(chat,pending['id'],'confirmed',invalid,'Original visible','mcp')
    assert review.get(chat,pending['id'])['status']=='pending'
    assert store.get(task)['result']=='Saved project name: Cedar'


@pytest.mark.parametrize('invalid', ['false', 'true', 0, 1, [], {}])
def test_settings_do_not_enable_remote_feedback_from_truthy_values(tmp_path, invalid):
    store,chats,chat,task,review=fixture(tmp_path)
    with pytest.raises(ValueError,match='boolean'):
        review.settings(chat,invalid,'browser')
    assert review.settings(chat)['enabled'] is False


def test_disabled_default_cached_packet_and_unavailable_not_confirmation(tmp_path):
    store,chats,chat,task,review=fixture(tmp_path)
    assert review.request(chat,task,'Was the name Cedar?',evidence_quote='Cedar')['status']=='disabled'
    review.settings(chat,True,'mcp')
    with pytest.raises(ValueError,match='evidence_quote'):
        review.request(chat,task,'Was the name Cedar?',evidence_quote='Quote from another task')
    first=review.request(chat,task,'Was the name Cedar?',evidence_quote='Cedar')
    assert first['id']==review.request(chat,task,'Was the name Cedar?',evidence_quote='Cedar')['id']
    result=review.respond(chat,first['id'],'confirmed',False,'Original chat unavailable','mcp')
    assert result['response']['verdict']=='unavailable'
    assert store.get(task)['result']=='Saved project name: Cedar'
    assert MemoryReview(Store(store.path)).get(chat,first['id'])['response']==result['response']
    with pytest.raises(Conflict):review.respond(chat,first['id'],'confirmed',True,'Changed answer','mcp')


def test_source_changes_scope_and_browser_dispatch_replay(tmp_path):
    store,chats,chat,task,review=fixture(tmp_path);review.settings(chat,True,'browser')
    first=review.request(chat,task,'Was the name Cedar?',evidence_quote='Cedar')
    assert review.claim_browser_dispatch(chat,first['id'])
    assert not review.claim_browser_dispatch(chat,first['id'])
    other=chats.create(chats.get(chat)['project_id'])['id']
    review.settings(other,True,'mcp')
    with pytest.raises(KeyError):review.request(other,task,'Cross-chat data')
    with pytest.raises(KeyError):review.get(other,first['id'])
    store.update(task,result='Corrected project name: Pine')
    assert review.get(chat,first['id'])['status']=='stale'
    with pytest.raises(Conflict):review.respond(chat,first['id'],'confirmed',True,'Old evidence','browser')
    second=review.request(chat,task,'Was the name Cedar?',evidence_quote='Pine')
    assert second['id']!=first['id'] and 'Pine' in second['request']['excerpt']


def test_saved_feedback_reenters_future_context_and_keeps_stale_status(tmp_path):
    store,chats,chat,task,review=fixture(tmp_path);review.settings(chat,True,'mcp')
    first=review.request(chat,task,'Name is Pine',evidence_quote='Cedar')
    review.respond(chat,first['id'],'contradicted',True,'The original source says Cedar','mcp')
    second=review.request(chat,task,'Name is Cedar',evidence_quote='Cedar')
    review.respond(chat,second['id'],'confirmed',False,'Original remote context absent','mcp')
    fresh=MemoryReview(Store(store.path));page=fresh.history(chat,limit=1)
    assert page['items'][0]['response']['verdict']=='unavailable'
    assert fresh.history(chat,page['next_after'])['items'][0]['response']['verdict']=='contradicted'
    followup=chats.submit(chat,'Continue with the correct name','inspect','followup')
    packet=fresh.memory.packet(followup['id'])
    assert 'contradicted' in packet and 'Original remote context absent' in packet
    store.update(task,result='Changed original')
    assert all(r['status']=='stale' for r in fresh.context(chat)['items'])
    assert store.get(task)['result']=='Changed original'
