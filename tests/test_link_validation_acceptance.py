import pytest
from hub.store import Store
from hub.conversations import Conversations
from hub.bridge_transcript import BridgeTranscript

@pytest.mark.parametrize("url", ["http://chatgpt.com/c/test", "https://evil.example/c/test", "https://chatgpt.com/c/test?token=x", "https://chatgpt.com/c/test#fragment"])
def test_direct_link_rejects_invalid_remote_without_mutation(tmp_path,url):
    store=Store(tmp_path/"hub.db")
    chats=Conversations(store)
    project=chats.project(str(tmp_path))
    chat=chats.create(project["id"])
    bridge=BridgeTranscript(store)
    original="https://chatgpt.com/c/original"
    bridge.link(chat["id"],original)
    with pytest.raises(ValueError):
        bridge.link(chat["id"],url)
    assert bridge.remote(chat["id"])==original
