import pytest
from hub.fara import parse_action,parse_message
from hub.errors import ObservationError
BODY='{"name":"computer_use","arguments":{"action":"left_click","coordinate":[77,867]}}'
def test_exact_observed_malformed_closing_tag():
 assert parse_action('<tool_call>'+BODY+'<tool_call>')==('click',{'point':'77 867'})
def test_constrained_json():
 assert parse_message({'content':BODY})==('click',{'point':'77 867'})
def test_multiple_objects_never_repaired():
 with pytest.raises(ObservationError):parse_action('<tool_call>'+BODY+'<tool_call>'+BODY)
