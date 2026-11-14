import pytest
from hub.fara import parse_message
from hub.errors import ObservationError
def test_server_extracted_function():
 m={'content':'I will click','tool_calls':[{'type':'function','function':{'name':'computer_use','arguments':'{"action":"left_click","coordinate":[174,750]}'}}]}
 assert parse_message(m)==('click',{'point':'174 750'})
def test_object_arguments():
 assert parse_message({'tool_calls':[{'function':{'name':'computer_use','arguments':{'action':'wait'}}}]})==('wait',{})
def test_multiple_calls_rejected():
 with pytest.raises(ObservationError):parse_message({'tool_calls':[{},{}]})
def test_unknown_tool_rejected():
 with pytest.raises(ObservationError):parse_message({'tool_calls':[{'function':{'name':'shell','arguments':{}}}]})
