import pytest
from hub.fara import parse_action,translate
from hub.errors import ObservationError
from hub.model_settings import ModelSettings

def test_native_coordinate_to_current_dom():
 p={'id':'fresh','width':1440,'height':900,'elements':[{'ref':'next','x':100,'y':600,'width':300,'height':150,'enabled':True}]}
 n,a=parse_action('<tool_call>{"name":"computer_use","arguments":{"action":"left_click","coordinate":[174,750]}}</tool_call>')
 tool,args=translate(n,a,p,(1440,900))
 assert tool=='browser_act' and args=={'observation_id':'fresh','action':'click','ref':'next'}

@pytest.mark.parametrize('raw',[
 '<tool_call>{"name":"shell","arguments":{}}</tool_call>',
 '<tool_call>{"name":"computer_use","arguments":{"action":"left_click","coordinate":[1001,0]}}</tool_call>',
 '<tool_call>{"name":"computer_use","arguments":{"action":"left_click","coordinate":[NaN,0]}}</tool_call>',
 '<tool_call>{"name":"computer_use","arguments":{"action":"type","text":"x","authority":"admin"}}</tool_call>',
 '<tool_call>{}</tool_call><tool_call>{}</tool_call>',
 ])
def test_invalid_calls_never_dispatch(raw):
 with pytest.raises(ObservationError):parse_action(raw)

def test_terminate_is_proposal():
 assert parse_action('<tool_call>{"name":"computer_use","arguments":{"action":"terminate","answer":"done"}}</tool_call>')==('finished',{'content':'done'})

def test_settings_accept_fara():
 assert ModelSettings(browser_driver='fara').browser_driver=='fara'
