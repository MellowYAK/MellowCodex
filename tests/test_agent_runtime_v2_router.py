"""P13 routing selection, privacy, provider health, fallback and latency."""
from dataclasses import replace
import statistics
import time
import pytest

from hub.agent_runtime_v2.router import (
    ProviderProfile,ProviderRegistry,ProviderHealth,RoutingRequest,
    ComputeMode,RouteError,route,
)


def profile(id,location="local",quality=.75,latency=500,reasoning=True,
            tools=True,ctx=32768,cost=0.0,health=ProviderHealth.HEALTHY,
            caps=frozenset({"chat","browser","code"})):
    return ProviderProfile(
        id=id,provider="Ollama" if location=="local" else "cloud-test",
        model=id,location=location,capabilities=caps,max_context=ctx,
        supports_reasoning=reasoning,supports_tools=tools,
        median_latency_ms=latency,measured_quality=quality,
        tool_success_rate=.93,estimated_usd_per_1k_tokens=cost,health=health,
    )


def request(**kwargs):
    base=dict(task_id="task",plan_version=1,
              required_capabilities=frozenset({"chat"}),complexity=.2,
              uncertainty=.2,context_tokens=2000)
    base.update(kwargs)
    return RoutingRequest(**base)


def test_deterministic_navigation_is_zero_model_calls():
    result=route(request(deterministic=True),ProviderRegistry())
    assert result.mode is ComputeMode.NONE and result.provider_id is None
    assert not result.think


def test_fast_prefers_low_latency_local():
    reg=ProviderRegistry([profile("slow",latency=2500),profile("fast",latency=100)])
    decision=route(request(),reg)
    assert decision.provider_id=="fast"
    assert decision.mode is ComputeMode.FAST_LOCAL
    assert decision.think is False
    assert decision.fallback_provider_ids==("slow",)


def test_deep_local_reasoning_enabled_by_complexity_and_failures():
    reg=ProviderRegistry([profile("fast-only",reasoning=False,latency=30),
                          profile("deep",reasoning=True,latency=400)])
    for kw in ({"complexity":.9},{"uncertainty":.85},{"prior_failures":2}):
        result=route(request(**kw),reg)
        assert result.provider_id=="deep"
        assert result.think and result.mode==ComputeMode.DEEP_LOCAL


@pytest.mark.parametrize("permission",[
    {"policy_allow_cloud":False,"user_cloud_approved":True},
    {"policy_allow_cloud":True,"user_cloud_approved":False},
    {"policy_allow_cloud":False,"user_cloud_approved":False},
])
def test_cloud_requires_both_policy_and_user_permission(permission):
    reg=ProviderRegistry([profile("cloud",location="cloud",quality=1,latency=1)])
    with pytest.raises(RouteError):
        route(request(complexity=.99,**permission),reg)


def test_sensitive_task_never_sends_to_cloud():
    reg=ProviderRegistry([profile("cloud",location="cloud",quality=1,latency=1),
                          profile("local",quality=.5,latency=2500)])
    selected=route(request(complexity=.95,sensitive=True,
                           user_cloud_approved=True,policy_allow_cloud=True),reg)
    assert selected.provider_id=="local" and selected.mode is ComputeMode.DEEP_LOCAL


def test_complex_task_can_choose_explicitly_approved_cloud():
    reg=ProviderRegistry([profile("cloud",location="cloud",quality=1,latency=80,cost=.0001),
                          profile("local",quality=.45,latency=4500)])
    result=route(request(complexity=.95,policy_allow_cloud=True,
                         user_cloud_approved=True),reg)
    assert result.provider_id=="cloud"
    assert result.mode==ComputeMode.CLOUD and result.think


def test_context_and_tool_capability_gate():
    reg=ProviderRegistry([profile("short",ctx=4000),profile("long",ctx=65536)])
    assert route(request(context_tokens=30000,needs_tools=True),reg).provider_id=="long"
    reg=ProviderRegistry([profile("no-tool",tools=False)])
    with pytest.raises(RouteError):
        route(request(needs_tools=True),reg)


def test_circuit_open_and_fallback_after_provider_failure():
    reg=ProviderRegistry([profile("fast",latency=40),profile("slow",latency=750)])
    assert route(request(),reg).provider_id=="fast"
    reg.replace_health("fast",ProviderHealth.CIRCUIT_OPEN)
    assert route(request(),reg).provider_id=="slow"
    reg.replace_health("slow",ProviderHealth.CIRCUIT_OPEN)
    with pytest.raises(RouteError):
        route(request(),reg)


def test_cost_budget_excludes_expensive_provider():
    reg=ProviderRegistry([profile("cloud",location="cloud",cost=10.0),
                          profile("local",cost=0)])
    result=route(request(complexity=.90,policy_allow_cloud=True,
                         user_cloud_approved=True,max_estimated_cost_usd=.03),reg)
    assert result.provider_id=="local"


def test_all_providers_disabled_or_unknown_capability_fails_closed():
    reg=ProviderRegistry([replace(profile("disabled"),enabled=False)])
    with pytest.raises(RouteError):
        route(request(),reg)
    reg=ProviderRegistry([profile("chat",caps=frozenset({"chat"}))])
    with pytest.raises(RouteError):
        route(request(required_capabilities=frozenset({"audio"})),reg)


def test_no_raw_prompt_or_private_reasoning_in_decision_record():
    reg=ProviderRegistry([profile("local")])
    result=route(request(),reg)
    record=result.decision_record()
    assert record.model_reference=="local"
    assert "reasoning_content" not in record.model_dump()
    assert "raw_prompt" not in record.model_dump()


def test_duplicate_ids_rejected_and_invalid_metadata_rejected():
    p=profile("q")
    with pytest.raises(ValueError):
        ProviderRegistry([p,p])
    with pytest.raises(ValueError):
        profile("bad",quality=2.0)
    with pytest.raises(ValueError):
        profile("bad2",ctx=0)


def test_fast_routing_metadata_p95_under_5ms():
    reg=ProviderRegistry([profile("p"+str(i),latency=80+i*25) for i in range(30)])
    times=[]
    for _ in range(250):
        start=time.perf_counter()
        route(request(),reg)
        times.append((time.perf_counter()-start)*1000)
    p95=sorted(times)[int(.95*len(times))]
    assert p95<5.0, "Metadata routing should not require any model call"
