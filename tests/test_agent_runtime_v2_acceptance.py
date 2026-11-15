"""P02: versioned, deterministic acceptance corpus for current Goal Board behavior.

Run with: python -m pytest -q tests/test_agent_runtime_v2_acceptance.py
Known gaps are strict XFAIL, not a hidden pass; turn green as the runtime verifier is integrated.
All cases use synthetic observations, not live accounts/credentials/external mutations.
"""
import json
from pathlib import Path
import pytest
from hub.browser_goal_board import seeded, progress

FILE=Path(__file__).resolve().parents[1]/"benchmarks"/"agent_runtime_v2"/"acceptance_v1.json"
DATA=json.loads(FILE.read_text(encoding="utf-8"))
CASES=DATA["cases"]

def page(url, controls=(), title="Walla", coherent=True):
    return {"tool":"browser_observe","state":"complete",
            "result":{"url":url,"title":title,"coherent":coherent,
                      "elements":list(controls)}}

HOME="https://www.walla.co.il/"
LINK={"tag":"a","name":"כניסה"}
PASS={"tag":"input","type":"password","name":"Password"}
EMAIL={"tag":"input","type":"email","name":"Email"}
def action(token):
    if token=="home":return page(HOME)
    if token=="home_login_link":return page(HOME,[LINK])
    if token=="home_newsletter":return page(HOME,[EMAIL],title="Walla homepage")
    if token=="home_incoherent":return page(HOME,coherent=False)
    if token=="other_home":return page("https://other.example/",[LINK])
    if token=="login_password":return page("https://www.walla.co.il/login",[PASS],title="Sign in")
    if token=="login_email":return page("https://www.walla.co.il/login",[EMAIL],title="Sign in")
    if token=="login_empty":return page("https://www.walla.co.il/login",title="Sign in")
    if token=="wrong_domain_password":return page("https://signin.attacker.example/login",[PASS],title="Login")
    if token=="lookalike_password":return page("https://evilwalla.co.il/login",[PASS],title="Login")
    if token=="subdomain_password":return page("https://account.walla.co.il/login",[PASS],title="Sign in")
    if token=="click_no_after":return {"tool":"browser_act","state":"complete","result":{"input_sent":True}}
    if token=="click_with_after":return {"tool":"browser_act","state":"complete","result":{"input_sent":True,"after":{"url":HOME+"pending","coherent":True}}}
    if token=="pending_click":return {"tool":"browser_act","state":"pending","result":{"input_sent":None}}
    if token=="failed_click":return {"tool":"browser_act","state":"failed","result":{"input_sent":False}}
    if token=="good_assess":return {"tool":"browser_assess","state":"complete","result":{"verified":True,"status":"success"}}
    if token=="bad_assess":return {"tool":"browser_assess","state":"complete","result":{"verified":False,"status":"success"}}
    if token=="failed_assess":return {"tool":"browser_assess","state":"complete","result":{"verified":False,"status":"failure"}}
    if token=="code_source":return {"tool":"context_search","state":"complete","result":{"items":[{"path":"hub/engine.py"}]}}
    if token=="code_write":return {"tool":"file_write","state":"complete","result":{"path":"example.txt"}}
    if token=="code_test":return {"tool":"candidate_test","state":"complete","result":{"verified":True}}
    if token=="code_pending":return {"tool":"file_write","state":"pending","result":{"input_sent":None}}
    if token=="desktop_observe":return {"tool":"desktop_status","state":"complete","result":{"window":"Settings"}}
    if token=="desktop_click":return {"tool":"desktop_action","state":"complete","result":{"input_sent":True}}
    if token=="inspect_source":return {"tool":"project_context","state":"complete","result":{"path":"README.md"}}
    raise AssertionError("Unknown fixture token: "+str(token))


def param(c):
    marks=[pytest.mark.xfail(strict=True,reason="Known gap: "+c["known_gap"])] if "known_gap" in c else []
    return pytest.param(c,id=c["id"]+"-"+c["name"],marks=marks)

@pytest.mark.parametrize("case",[param(x) for x in CASES])
def test_goal_board_acceptance_baseline(case):
    board=seeded(case["goal"],task_mode=case["mode"])
    actions=[action(t) for t in case["tokens"]]
    actual=progress(board,actions,task_state=case["task_state"])
    assert actual["done"] is case["expected_done"], (
        case["id"],case["name"],"expected",case["expected_done"],"actual",actual
    )


def test_corpus_integrity_and_risk_free_inputs():
    assert DATA["version"]==1
    assert len(CASES)>=25
    ids=[c["id"] for c in CASES]
    assert len(ids)==len(set(ids))
    assert {"browser","code","desktop","inspect"}=={c["mode"] for c in CASES}
    assert not any("known_gap" in c for c in CASES)
    for c in CASES:
        assert not any(k in c["goal"].lower() for k in ("password=","token=","api_key="))
        assert len(c["tokens"])<=8
        for token in c["tokens"]:action(token)


def test_pending_input_never_counts_as_verified_completion():
    c=next(x for x in CASES if x["id"]=="B07")
    result=progress(seeded(c["goal"]),[action(t) for t in c["tokens"]])
    assert result["uncertain"] and not result["done"]
    assert any(step["status"]=="uncertain" for step in result["steps"])
