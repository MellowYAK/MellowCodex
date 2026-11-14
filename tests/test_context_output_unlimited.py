"""Output ceiling is model/context dependent, not an arbitrary half window."""
from hub.model_context import build_adaptive_packet


def test_short_input_can_use_more_than_half_context_for_output():
    packet,info=build_adaptive_packet(
        [{"role":"system","content":"Mandatory instructions"},
         {"role":"user","content":"Write a long answer"}],[],
        32768,100000,target_tokens=12000,task_id="b"*32)
    assert info["configured_output_ceiling"]==100000
    assert info["reserved_output"]>16384
    assert info["reserved_output"]+info["estimated_input"]+info["accounting_margin"]<=32768


def test_explicit_smaller_output_limit_stays_honored():
    _,info=build_adaptive_packet(
        [{"role":"system","content":"System"},{"role":"user","content":"Hello"}],
        [],32768,1234,target_tokens=12000)
    assert info["reserved_output"]<=1234
    assert info["reserved_output"]>=256
