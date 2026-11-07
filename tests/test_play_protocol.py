from hub.play_protocol import protocol,instructions
from hub.tools import CATALOG


def test_play_protocol_is_current_catalog_with_explicit_transport_limits():
    value=protocol()
    assert value['name']=='PLAY' and value['version']=='2'
    assert 'different agent instance' in value['rules'][0]
    assert {t['name'] for t in value['local_tool_catalog']}=={t['function']['name'] for t in CATALOG}
    assert 'local_agent_action' in value['request']
    assert value['sha256']==protocol()['sha256']
    text=instructions('local-test-chat')
    assert 'local-test-chat' in text and 'project_index_status' in text
    assert 'not success' in text and 'unavailable' in text
    assert 'not implemented' in text
