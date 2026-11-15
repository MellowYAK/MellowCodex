"""P03 contracts: typed plans, dependency DAG, evidence and decisions."""
from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError
from hub.agent_runtime_v2.contracts import (
    AcceptanceCriterion, PlanStep, TaskPlan, Evidence, DecisionRecord,
    ActionRecord, FeedbackStatus, ToolRisk, stable_action_key,
)

def criterion(name="url"):
    return AcceptanceCriterion(id=name, description="Verified destination", verifier_type="url",
                               expected={"host":"walla.co.il"})

def step(ident,version=1,deps=()):
    return PlanStep(id=ident,plan_version=version,objective="Verify "+ident,
                    dependencies=list(deps),acceptance=[criterion(ident)])

def plan(*steps,version=1):
    return TaskPlan(task_id="t1",version=version,goal="Reach the login form",
                    steps=list(steps) if steps else [step("start")],
                    completion_criteria=[criterion("final")])


def test_roundtrip_versioned_plan_and_acyclic_deps():
    p=plan(step("open"),step("find",deps=["open"]),step("verify",deps=["find"]))
    assert [x.id for x in p.steps]==["open","find","verify"]
    assert TaskPlan.model_validate_json(p.model_dump_json())==p
    assert p.steps[-1].dependencies==["find"]


@pytest.mark.parametrize("items",[
    [step("same"),step("same")],
    [step("go",deps=["missing"])],
    [step("one",deps=["two"]),step("two",deps=["one"])],
    [step("old",version=2)],
])
def test_invalid_plan_edges_or_versions_rejected(items):
    with pytest.raises(ValidationError):
        plan(*items)


def test_cannot_create_plan_without_final_required_acceptance():
    with pytest.raises(ValidationError):
        TaskPlan(task_id="x",version=1,goal="Test",steps=[step("one")],
                 completion_criteria=[criterion("optional").model_copy(update={"required":False})])


@pytest.mark.parametrize("bad",["","    "])
def test_blank_goal_rejected(bad):
    with pytest.raises(ValidationError):
        TaskPlan(task_id="x",version=1,goal=bad,steps=[step("one")],
                 completion_criteria=[criterion("final")])


def test_duplicate_acceptance_id_rejected():
    with pytest.raises(ValidationError):
        PlanStep(id="a",plan_version=1,objective="test",
                 acceptance=[criterion("x"),criterion("x")])


def evidence(**updates):
    data=dict(evidence_id="e1",task_id="t1",step_id="s1",source="browser",
              observed_at=datetime(2026,11,15,tzinfo=timezone.utc),
              content_hash="abcdef",sanitized_payload={"host":"walla.co.il"})
    data.update(updates)
    return Evidence(**data)


def test_evidence_freshness_boundary_and_future_guard():
    at=datetime(2026,11,15,tzinfo=timezone.utc)
    e=evidence(freshness_deadline=at+timedelta(seconds=2))
    assert e.is_fresh(at+timedelta(seconds=1),max_age_ms=1500)
    assert not e.is_fresh(at+timedelta(seconds=3))
    assert not e.is_fresh(at-timedelta(seconds=1))
    assert not e.is_fresh(at+timedelta(seconds=2),max_age_ms=1000)


@pytest.mark.parametrize("bad",[
    {"observed_at":datetime(2026,11,15)},
    {"freshness_deadline":datetime(2026,11,15)},
    {"freshness_deadline":datetime(2026,11,14,tzinfo=timezone.utc)},
])
def test_invalid_evidence_timestamps(bad):
    with pytest.raises(ValidationError):
        evidence(**bad)


def test_only_safe_decision_records_without_raw_private_reasoning():
    ok=DecisionRecord(decision_id="d",task_id="t1",plan_version=1,
                      decision="navigate_to_login",reason_code="goal_not_satisfied",
                      chosen_strategy="click_observed_login_link",input_evidence_ids=["e1"])
    assert ok.reason_code=="goal_not_satisfied"
    with pytest.raises(ValidationError):
        DecisionRecord(**{**ok.model_dump(),"reasoning_content":"secret thoughts"})


def test_effect_key_stable_over_dict_order_and_plan_revisions():
    a=stable_action_key("task","publish","youtube/channel-123",{"title":"test","visibility":"private"})
    b=stable_action_key("task","publish","youtube/channel-123",{"visibility":"private","title":"test"})
    c=stable_action_key("task","publish","youtube/channel-456",{"title":"test","visibility":"private"})
    assert a==b and a!=c and len(a)==64


def test_action_record_explicit_risk_and_unknown_result():
    a=ActionRecord(action_id="a",idempotency_key="a"*64,task_id="t1",
                   step_id="s1",effect_name="publish",risk_level=ToolRisk.EXTERNAL_EFFECT,
                   dispatch_state="unknown")
    assert a.outcome_state is FeedbackStatus.UNCERTAIN
    with pytest.raises(ValidationError):
        a.model_copy(update={"risk_level":"R7"}).model_validate(a.model_dump()|{"risk_level":"R7"})


def test_self_dependency_and_duplicate_dependencies_rejected():
    with pytest.raises(ValidationError):
        step("x",deps=["x"])
    with pytest.raises(ValidationError):
        step("x",deps=["z","z"])


def test_no_mutation_of_frozen_task_plan():
    p=plan()
    with pytest.raises(ValidationError):
        p.version=2
