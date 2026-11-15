"""Browser-only fast policy retains tool safety and global model configuration."""
from hub.browser_fast_policy import adapt_browser_policy
from hub.model_settings import ModelSettings


def tool(name):
    return {"type":"function","function":{"name":name,"description":"mock tool","parameters":{"type":"object","properties":{}}}}


def test_browser_policy_clamps_response_and_input_without_mutating_preferences():
    original=ModelSettings(context_tokens=32768,response_tokens=25000,working_input_tokens=12000)
    names=["conversation_history","run_shell","agent_environment","browser_navigate","browser_observe","browser_act","browser_assess","browser_tabs","browser_pointer"]
    active,selected,meta=adapt_browser_policy(original,[tool(n) for n in names])
    assert original.response_tokens==25000
    assert original.context_tokens==32768
    assert active.context_tokens==32768
    assert active.response_tokens==1024
    assert active.working_input_tokens==5200
    chosen={t["function"]["name"] for t in selected}
    assert {"agent_environment","browser_navigate","browser_observe","browser_act","browser_assess","browser_tabs","browser_pointer"}<=chosen
    assert "conversation_history" not in chosen
    assert "run_shell" not in chosen
    assert meta["durable_messages_changed"] is False


def test_browser_policy_respects_already_smaller_response_ceiling_and_custom_target():
    original=ModelSettings(response_tokens=512,working_input_tokens=2800)
    out,items,meta=adapt_browser_policy(original,[tool("browser_observe"),tool("browser_act")])
    assert out.response_tokens==512
    assert out.working_input_tokens==2800
    assert len(items)==2


def test_browser_fast_history_hint_does_not_demand_history_for_ordinary_navigation():
    from pathlib import Path
    source=Path(__file__).parents[1].joinpath("hub","engine.py").read_text(encoding="utf-8")
    assert "if task['mode']=='browser':" in source
    assert "use agent_environment for named local apps" in source
