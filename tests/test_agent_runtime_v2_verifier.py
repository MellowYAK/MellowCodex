"""P07: fail-closed verification of original goal against fresh plan-bound evidence."""
from datetime import datetime,timedelta,timezone
import uuid
import pytest
from hub.browser_goal_board import seeded
from hub.agent_runtime_v2.goal_board_adapter import adapt_board
from hub.agent_runtime_v2.contracts import Evidence
from hub.agent_runtime_v2.verifier import verify_plan

NOW=datetime(2026,11,15,12,0,tzinfo=timezone.utc)
HOST="https://www.walla.co.il/"
LOGIN="https://www.walla.co.il/login"


def e(step, payload,tool,*,urlhost=None,task="task",version=1,status="SUCCESS",
      source="browser",at=NOW,target="tab-1",verified_by=None):
    provenance={"plan_version":version,"status":status,"tool_name":tool}
    if verified_by:provenance["verified_by"]=verified_by
    return Evidence(
        evidence_id=uuid.uuid4().hex,task_id=task,step_id=step,source=source,
        observed_at=at,tool_call_id=uuid.uuid4().hex,target_id=target,
        content_hash="abcdef123",sanitized_payload=payload,provenance=provenance,
        freshness_deadline=at+timedelta(seconds=5),
    )


def login_plan(version=1,task="task"):
    return adapt_board(seeded("Open Walla and show the התחברות login form"),task,plan_version=version)


def page(url,controls=(),title="Walla"):
    return {"url":url,"coherent":True,"title":title,"elements":list(controls)}


def base_evidence(host=HOST,login_host=LOGIN,assess=True,form=True):
    home=e("entry",page(host),"browser_observe")
    find=e("discover",page(host,[{"tag":"a","name":"כניסה"}]),"browser_observe",at=NOW+timedelta(milliseconds=100))
    act=e("act",{"input_sent":True,"after":page(login_host)},"browser_act",at=NOW+timedelta(milliseconds=200))
    elements=[{"tag":"input","type":"password","name":"סיסמה"}] if form else []
    final=e("final",page(login_host,elements,title="Sign in"),"browser_observe",at=NOW+timedelta(milliseconds=300))
    out=[home,find,act,final]
    if assess:
        out.append(e("final",{"verified":True,"status":"success"},"browser_assess",at=NOW+timedelta(milliseconds=400)))
    return out


def verify(evidence,plan=None,at=NOW+timedelta(milliseconds=900)):
    return verify_plan(plan or login_plan(),evidence,at=at)


def test_positive_original_login_goal_with_form_and_assessment():
    report=verify(base_evidence())
    assert report.completed
    assert all(value for _,value in report.steps)
    assert report.final[0].reason_code=="login_form_with_assessment"


@pytest.mark.parametrize("host",[
    "https://signin.attacker.example/login",
    "https://evilwalla.co.il/login",
    "https://walla.co.il.evil.example/login",
    "https://walla.co.il@evil.example/login",
])
def test_wrong_or_lookalike_host_cannot_complete(host):
    assert not verify(base_evidence(login_host=host)).completed


def test_final_homepage_with_assessment_not_form():
    assert not verify(base_evidence(login_host=HOST,form=False)).completed


def test_login_form_without_assessment_does_not_complete():
    assert not verify(base_evidence(assess=False)).completed


def test_unauthorized_assessment_before_page_not_accepted():
    items=base_evidence()
    a=items[-1]
    items[-1]=a.model_copy(update={"observed_at":NOW})
    assert not verify(items).completed


def test_assessment_for_different_tab_rejected():
    items=base_evidence()
    items[-1]=items[-1].model_copy(update={"target_id":"tab-2"})
    assert not verify(items).completed


def test_pending_or_unverified_effect_does_not_complete():
    items=base_evidence()
    items[2]=items[2].model_copy(update={"provenance":{**items[2].provenance,"status":"UNCERTAIN"}})
    assert not verify(items).completed
    assert any(x.startswith("act:") for x in verify(items).missing_criteria)


def test_stale_evidence_cannot_complete():
    assert not verify(base_evidence(),at=NOW+timedelta(seconds=6)).completed


def test_wrong_task_or_plan_revision_evidence_cannot_complete():
    items=base_evidence()
    assert not verify(items,plan=login_plan(version=2)).completed
    items[3]=items[3].model_copy(update={"task_id":"another"})
    assert not verify(items).completed


def test_direct_login_without_confirmed_action_not_sufficient_to_claim_all_steps():
    items=base_evidence()
    items=[x for x in items if x.step_id!="act"]
    assert not verify(items).completed


def test_login_email_first_legitimate_form():
    items=base_evidence()
    items[3]=items[3].model_copy(update={
        "sanitized_payload":page(LOGIN,[{"tag":"input","type":"email","name":"Email"}],"Sign in")})
    assert verify(items).completed


def test_email_newsletter_without_login_context_not_form():
    items=base_evidence()
    items[3]=items[3].model_copy(update={
        "sanitized_payload":page(HOST,[{"tag":"input","type":"email","name":"Newsletter"}],"Walla")})
    assert not verify(items).completed


def test_legitimate_account_subdomain_accepted():
    items=base_evidence(login_host="https://account.walla.co.il/login")
    assert verify(items).completed


def test_source_worker_cannot_forge_browser_control_evidence():
    items=base_evidence()
    items[3]=items[3].model_copy(update={"source":"worker"})
    assert not verify(items).completed


def test_code_done_state_without_trusted_goal_assertion_is_not_success():
    p=adapt_board(seeded("Modify code and test",task_mode="code"),"task")
    obs=e("entry",{"source_observed":True,"terminal_task_state":"done"},
          "context_search",source="tool")
    assert not verify_plan(p,[obs],at=NOW+timedelta(seconds=1)).completed


def test_desktop_done_without_actual_verified_effect_is_not_success():
    p=adapt_board(seeded("Open settings and change control",task_mode="desktop"),"task")
    seen=[e("entry",{"source_observed":True,"terminal_task_state":"done"},
            "desktop_status",source="desktop")]
    assert not verify_plan(p,seen,at=NOW+timedelta(seconds=1)).completed


def test_code_full_trusted_step_and_goal_attestations_pass():
    p=adapt_board(seeded("Implement code and verify",task_mode="code"),"task")
    expected={"entry":"source_observed","discover":"route_or_evidence_identified",
              "act":"tool_effect_verified","final":"final_goal_verified"}
    entries=[]
    for step in p.steps:
        payload={expected[step.id]:True}
        if step.id=="final":payload["terminal_task_state"]="done"
        entries.append(e(step.id,payload,"deterministic_verifier",source="tool",verified_by="deterministic"))
    assert verify_plan(p,entries,at=NOW+timedelta(seconds=1)).completed


def test_untrusted_worker_claiming_final_verified_is_rejected():
    p=adapt_board(seeded("Inspect source",task_mode="inspect"),"task")
    evidence=[e(step.id,{"source_observed":True,"route_or_evidence_identified":True,
                     "tool_effect_verified":True,"final_goal_verified":True,
                     "terminal_task_state":"done"},
               "worker_proposal",source="worker",verified_by="deterministic") for step in p.steps]
    assert not verify_plan(p,evidence,at=NOW+timedelta(seconds=1)).completed
