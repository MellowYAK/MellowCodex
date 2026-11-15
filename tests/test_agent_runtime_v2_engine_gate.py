"""P14 production browser completion gating: feature flag compatibility."""
import time
from hub.browser_goal_board import seeded
from hub.agent_runtime_v2.engine_gate import browser_goal_complete


def page(url,controls=(),title="Walla"):
    return {"tool":"browser_observe","state":"complete",
            "result":{"url":url,"title":title,"coherent":True,
                      "elements":list(controls)}}


def assessment(goal,**kwargs):
    return {"tool":"browser_assess","state":"complete",
            "result":{"status":"success","verified":True,
                      "goal_verified":True,"original_goal":goal,
                      "checked_at":time.time(),**kwargs}}


def test_legacy_login_remains_guarded_when_flag_off():
    b=seeded("Open Walla and show login form")
    assert not browser_goal_complete(b,[page("https://www.walla.co.il/")],strict=False)


def test_known_homepage_proven_without_model_or_click():
    b=seeded("Open Walla homepage")
    assert browser_goal_complete(b,[page("https://www.walla.co.il/")],strict=True)
    assert not browser_goal_complete(b,[page("https://walla.co.il.evil.invalid/")],strict=True)


def test_search_homepage_not_final_even_when_assessment_claims_success():
    b=seeded("Find the exact result on Walla")
    p=page("https://www.walla.co.il/")
    assert not browser_goal_complete(b,[p],strict=True)
    assert not browser_goal_complete(b,[p,{"tool":"browser_assess","state":"complete",
                "result":{"status":"success","verified":True}}],strict=True)


def test_explicit_goal_bound_assessment_required_for_search():
    b=seeded("Find the exact result on Walla")
    actions=[page("https://www.walla.co.il/news/search"),assessment(b["goal"])]
    assert browser_goal_complete(b,actions,strict=True)
    actions[-1]["result"]["original_goal"]="Open Walla"
    assert not browser_goal_complete(b,actions,strict=True)


def test_assessment_from_other_domain_does_not_pass():
    b=seeded("Find the exact result on Walla")
    assert not browser_goal_complete(b,[page("https://walla.co.il.evil.invalid/result"),
                                        assessment(b["goal"])],strict=True)


def test_expired_assessment_cannot_complete():
    b=seeded("Find the exact result on Walla")
    a=assessment(b["goal"])
    a["result"]["checked_at"]=time.time()-150
    assert not browser_goal_complete(b,[page("https://www.walla.co.il/news"),a],
                                      strict=True)


def test_pending_action_blocks_completed_claim():
    b=seeded("Find the exact result on Walla")
    actions=[page("https://www.walla.co.il/news"),
             {"tool":"browser_act","state":"pending","result":{"input_sent":None}},
             assessment(b["goal"])]
    assert not browser_goal_complete(b,actions,strict=True)


def test_legacy_nonsignin_keeps_existing_policy_off():
    b=seeded("Find exact result on Walla")
    assert browser_goal_complete(b,[],strict=False)


def test_strict_without_board_fails_closed():
    assert not browser_goal_complete(None,[],strict=True)


def test_login_wrong_final_domain_blocked():
    b=seeded("Open Walla and show login form")
    actions=[
        page("https://www.walla.co.il/",[{"tag":"a","name":"כניסה"}]),
        {"tool":"browser_act","state":"complete","result":{"input_sent":True,
                "after":{"url":"https://signin.attacker.example/login","coherent":True}}},
        page("https://signin.attacker.example/login",[{"tag":"input","type":"password"}],"Sign in"),
        {"tool":"browser_assess","state":"complete","result":{"status":"success",
                  "verified":True}},
    ]
    assert not browser_goal_complete(b,actions,strict=True)
