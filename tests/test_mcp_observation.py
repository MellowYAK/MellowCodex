import asyncio
import pytest
from hub.store import Store
from hub.conversations import Conversations
from hub.bridge_transcript import BridgeTranscript
from hub.mcp_observation import record_observation
from hub.context.tools import register_mcp


def test_mcp_reads_persist_in_same_chat_and_reject_wrong_project(tmp_path):
    c=Conversations(Store(tmp_path/'state.db'));p=c.project(str(tmp_path))
    chat=c.create(p['id'],conversation_key='chatgpt:read-test');t=BridgeTranscript(c.store)
    class Registry:
        def __init__(self):self.tools={}
        def tool(self,**kwargs):
            def register(fn):self.tools[fn.__name__]=fn;return fn
            return register
    registry=Registry()
    async def local(path,data=None,timeout=15):
        if path.endswith('/mcp-observation'):
            return record_observation(c,t,path.split('/')[3],data)
        return {'source_files':44}
    register_mcp(registry,local,None,None)
    result=asyncio.run(registry.tools['project_context'](p['id'],chat['id']))
    assert result['source_files']==44
    asyncio.run(registry.tools['context_search'](p['id'],chat['id'],'video'))
    messages=t.list(chat['id'])
    assert len(messages)==4 and messages[-1]['status']=='completed'
    assert len(c.inventory()['chats'])==1
    with pytest.raises(ValueError):
        asyncio.run(registry.tools['project_context']('wrong-project',chat['id']))
    assert len(t.list(chat['id']))==4
