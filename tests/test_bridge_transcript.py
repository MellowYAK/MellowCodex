from hub.bridge_transcript import BridgeTranscript
from hub.store import Store
from hub.preferences import save_presentation,load_presentation

def test_connection_preferences_survive_reopen_and_relink_is_atomic(tmp_path):
    import pytest
    from hub.conversations import Conversations
    store=Store(tmp_path/'connections.sqlite3');chats=Conversations(store)
    project=chats.project(str(tmp_path));first=chats.create(project['id'])['id'];second=chats.create(project['id'])['id']
    log=BridgeTranscript(store)
    url='https://chatgpt.com/c/first'
    log.configure(first,'play',True,url)
    log.configure(second,'mcp',True,'https://chatgpt.com/c/second')
    with pytest.raises(ValueError):log.configure(second,'play',False,url)
    restored=BridgeTranscript(Store(store.path))
    assert restored.connection(second)['transport']=='mcp'
    assert restored.connection(second)['favorite'] is True
    assert len(restored.favorites())==2
    for invalid in ['https://evil.example/c/first','https://chatgpt.com@evil.example/c/first','http://chatgpt.com/c/first','https://chatgpt.com/c/first?token=private']:
        with pytest.raises(ValueError):log.configure(first,url=invalid)
    assert restored.remote(first)==url
    log.configure(first,url='https://chatgpt.com/c/relinked')
    assert log.local(url) is None and log.remote(first).endswith('/relinked')


def test_correspondence_is_durable_deduplicated_and_includes_files(tmp_path):
    store=Store(tmp_path/'db.sqlite3');log=BridgeTranscript(store)
    log.append('chat1','local_agent','agent_to_chatgpt','Question','q1',status='sending')
    log.append('chat1','local_agent','agent_to_chatgpt','Question','q1')
    log.delivery('chat1','q1',[{'id':'file1','name':'proof.txt'}],'sent')
    log.append('chat1','chatgpt','chatgpt_to_agent','Answer','r1')
    log.append('chat2','user','user_to_chatgpt','Different conversation','u1')
    reopened=BridgeTranscript(Store(tmp_path/'db.sqlite3')).list('chat1')
    assert len(reopened)==2 and reopened[0]['status']=='sent'
    assert reopened[0]['files']==[{'id':'file1','name':'proof.txt'}]
    assert reopened[1]['text']=='Answer'


def test_last_presentation_is_global_not_per_chat(tmp_path):
    assert load_presentation(tmp_path)=='split'


def test_input_modes_persist_without_overwriting_presentation(tmp_path,monkeypatch):
    from hub.preferences import save_input_mode,load_input_mode
    from hub.tools import ToolRunner
    save_presentation(tmp_path,'background');save_input_mode(tmp_path,'quiet')
    assert load_input_mode(tmp_path)=='quiet' and load_presentation(tmp_path)=='background'
    monkeypatch.setattr('hub.tools.STATE',tmp_path)
    runner=ToolRunner()
    names=lambda:{t['function']['name'] for t in runner.catalog('desktop')}
    assert 'desktop_action' not in names() and 'window_act' in names()
    save_input_mode(tmp_path,'physical');save_presentation(tmp_path,'split')
    assert load_input_mode(tmp_path)=='physical'
    assert 'desktop_action' in names() and 'window_act' not in names()
    save_input_mode(tmp_path,'auto')
    assert {'desktop_action','window_act'}<=names()


def test_each_local_chat_keeps_its_remote_binding(tmp_path):
    import asyncio
    from types import SimpleNamespace
    from hub.bridge_controller import BridgeController
    from hub.conversations import Conversations
    async def run():
        store=Store(tmp_path/'db.sqlite3');conversations=Conversations(store)
        project=conversations.project(str(tmp_path));first=conversations.create(project['id']);second=conversations.create(project['id'])
        class Bridge:
            preferred_url=None;bound_url=None;pending={'users':0,'user_id':'outbound'}
            def __init__(self):self.opened=[]
            async def open_conversation(self,url=None):
                self.opened.append(url);self.bound_url=url or 'https://chatgpt.com/c/session-'+str(len(self.opened));return {'ready':True}
        bridge=Bridge();controller=BridgeController(SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=bridge),lock=asyncio.Lock()))
        await controller.select_context(first['id']);controller.record_outbound('First question');controller.record_delivery({'sent':True,'files':[]});controller.record_answer({'text':'First answer','fingerprint':'answer1'})
        first_url=bridge.bound_url
        await controller.select_context(second['id']);controller.record_outbound('Second question');controller.record_delivery({'sent':True,'files':[]})
        assert bridge.bound_url!=first_url
        await controller.select_context(first['id']);assert bridge.opened[-1]==first_url
        assert [m['text'] for m in controller.transcript.list(first['id'])]==['First question','First answer']
        assert [m['text'] for m in controller.transcript.list(second['id'])]==['Second question']
    asyncio.run(run())


def test_no_outbound_message_is_orphaned(tmp_path):
    import asyncio
    from types import SimpleNamespace
    from hub.bridge_controller import BridgeController
    from hub.conversations import Conversations
    store=Store(tmp_path/'db.sqlite3');conversations=Conversations(store);conversations.project(str(tmp_path))
    bridge=SimpleNamespace(bound_url=None)
    controller=BridgeController(SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=bridge),lock=asyncio.Lock()))
    controller.record_outbound('A short question')
    chat_id=controller.state['chat_id']
    assert conversations.get(chat_id)
    assert controller.transcript.list(chat_id)[0]['text']=='A short question'
    save_presentation(tmp_path,'background');assert load_presentation(tmp_path)=='background'
    save_presentation(tmp_path,'split');assert load_presentation(tmp_path)=='split'
    # Starting any new chat does not modify the global preference.
    from hub.conversations import Conversations
    chats=Conversations(Store(tmp_path/'db.sqlite3'));project=chats.project(str(tmp_path))
    chats.create(project['id']);chats.create(project['id'])
    assert load_presentation(tmp_path)=='split'


def test_stopped_uncertain_send_survives_restart_and_cannot_be_discarded_by_reconnect(tmp_path):
    import asyncio
    import pytest
    from types import SimpleNamespace
    from hub.bridge_controller import BridgeController
    from hub.conversations import Conversations
    async def run():
        store=Store(tmp_path/'db.sqlite3');chats=Conversations(store)
        project=chats.project(str(tmp_path));first=chats.create(project['id']);second=chats.create(project['id'])
        engine=SimpleNamespace(store=store,runner=SimpleNamespace(chatgpt=SimpleNamespace(bound_url=None)),lock=asyncio.Lock())
        controller=BridgeController(engine)
        controller.state.update(chat_id=first['id'],enabled=True,continuous=True,phase='send_uncertain',pending_outbound_text='Unconfirmed request',outbound_key='pending-1')
        controller.transcript.append(first['id'],'local_agent','agent_to_chatgpt','Unconfirmed request','pending-1',status='sending')
        controller.stop()
        controller=BridgeController(engine)
        before=controller.state.copy()
        with pytest.raises(ValueError,match='Reconcile'):
            await controller.select_context(second['id'])
        with pytest.raises(ValueError,match='Reconcile'):
            await controller.listen(project['id'],chat_id=first['id'])
        assert controller.state==before
        assert controller.transcript.list(first['id'])[0]['status']=='sending'
        assert (await controller.select_context(first['id']))['id']==first['id']
    asyncio.run(run())


def test_draft_ownership_requires_complete_local_outbound_text(tmp_path):
    log=BridgeTranscript(Store(tmp_path/'db.sqlite3'))
    log.append('first','local_agent','agent_to_chatgpt','PLAY\nOriginal full instructions','own',status='sending')
    log.append('second','user','user_to_chatgpt','Human draft','human')
    assert log.owned_draft('PLAY\r\nOriginal full instructions')['chat_id']=='first'
    assert log.owned_draft('PLAY\nOriginal full instructions')['status']=='sending'
    assert log.owned_draft('PLAY') is None
    assert log.owned_draft('PLAY\nOriginal full instructions plus human edits') is None
    assert log.owned_draft('Human draft') is None
    assert log.owned_draft('') is None
