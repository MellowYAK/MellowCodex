import pytest
from hub.model_protocol import normalize_message

CATALOG=[{'type':'function','function':{'name':'allowed_tool','parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path'],'additionalProperties':False}}}]

def test_exact_legacy_envelope_normalized_against_allowed_schema():
    message,changed=normalize_message({'role':'assistant','content':' {"name":"allowed_tool","arguments":{"path":"file.py"}} '},CATALOG)
    assert changed and message['tool_calls'][0]['function']['arguments']=={'path':'file.py'}

@pytest.mark.parametrize('text',[
    'Example: {"name":"allowed_tool","arguments":{"path":"file.py"}}',
    '```json\n{"name":"allowed_tool","arguments":{"path":"file.py"}}\n```',
    '{"name":"unknown","arguments":{"path":"file.py"}}',
    '{"name":"allowed_tool","arguments":{}}',
    '{"name":"allowed_tool","arguments":{"path":"file.py","command":"bad"}}',
    '[{"name":"allowed_tool","arguments":{"path":"file.py"}}]',
])
def test_never_extract_calls_from_ambiguous_or_invalid_text(text):
    original={'role':'assistant','content':text}
    assert normalize_message(original,CATALOG)==(original,False)
