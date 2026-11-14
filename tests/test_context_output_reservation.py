"""Adaptive output reservation under a 16K context with a 16K output ceiling."""
import copy
import pytest
from hub.model_context import build_adaptive_packet, ContextBudgetError


def test_context_equals_output_ceiling_does_not_starve_mandatory_messages():
    messages=[{'role':'system','content':'Mandatory policy and project rules.'*20},
              {'role':'user','content':'Create isolated candidate only.'}]
    original=copy.deepcopy(messages)
    packet,diag=build_adaptive_packet(messages,[],16000,16000,
                                      target_tokens=12000,task_id='a'*32)
    assert packet==messages
    assert messages==original
    assert 256<=diag['reserved_output']<16000
    assert diag['configured_output_ceiling']==16000
    assert diag['output_reservation_adjusted'] is True
    assert diag['estimated_input']+diag['reserved_output']+diag['accounting_margin']<=16000


def test_budget_dynamically_shrinks_output_without_dropping_requirement():
    important='MUST_KEEP_THIS_GUIDANCE'
    messages=[{'role':'system','content':important+' instructions '+('x'*23000)},
              {'role':'user','content':'Original objective'}]
    packet,diag=build_adaptive_packet(messages,[],16000,16000)
    assert important in packet[0]['content']
    assert packet[1]['content']=='Original objective'
    assert diag['output_reservation_retries']>=1
    assert diag['reserved_output']<8000


def test_impossible_mandatory_input_fails_explicitly():
    messages=[{'role':'system','content':'Essential '+('x'*55000)},
              {'role':'user','content':'Never drop this'}]
    with pytest.raises(ContextBudgetError) as error:
        build_adaptive_packet(messages,[],16000,16000)
    assert error.value.diagnostic['minimum_output_reservation']==256
    assert error.value.diagnostic['configured_output_ceiling']==16000
