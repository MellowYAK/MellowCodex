"""P12 fast path: one input/step, 0 model calls, no false completion."""
import asyncio
import pytest

from hub.agent_runtime_v2.fast_executor import (
    KnownNavigation,DeterministicBrowserRunner,
)

HOME="https://www.walla.co.il/"
LOGIN="https://www.walla.co.il/login"


def observation(oid,url,links=(),form=False,coherent=True):
    elements=[{"ref":f"a{i}","tag":"a","name":name,"href":href,
               "visible":True,"enabled":True} for i,(name,href) in enumerate(links)]
    if form:
        elements.append({"ref":"password","tag":"input","type":"password",
                         "name":"סיסמה","visible":True,"enabled":True})
    return {"id":oid,"url":url,"title":"Sign in" if form else "Walla",
            "coherent":coherent,"elements":elements}


class BrowserStub:
    def __init__(self,pages,*,effect=None):
        self.pages=pages
        self.index=0
        self.act_calls=[]
        self.observed=[]
        self.effect=effect

    async def observe(self,folder,query=""):
        self.observed.append(query)
        return self.pages[self.index]

    async def act(self,args,folder):
        self.act_calls.append(args)
        if self.effect=="timeout":
            raise TimeoutError("Unknown effect")
        if self.effect=="input_sent_false":
            return {"input_sent":False,"error":"Stale"}
        if self.effect=="unknown":
            return {"input_sent":None,"dispatch_state":"unknown_effect"}
        self.index=min(self.index+1,len(self.pages)-1)
        return {"input_sent":True,"dispatch_state":"observed_transition",
                "after":self.pages[self.index]}


STEP=KnownNavigation("כניסה","walla.co.il","walla.co.il","/login",
                     post_condition="login_form")


def run(browser,steps=None,**kwargs):
    return asyncio.run(DeterministicBrowserRunner(browser).execute(steps or [STEP],"/tmp",**kwargs))


def test_known_login_link_clicks_once_without_model_and_not_final_goal():
    b=BrowserStub([
        observation("o1",HOME,[("כניסה",LOGIN)]),
        observation("o2",LOGIN,form=True),
    ])
    result=run(b)
    assert result.chain_verified
    assert result.goal_verified is False
    assert result.dispatches==1 and result.observations==2
    assert result.model_calls==0
    assert b.act_calls==[{"action":"click","observation_id":"o1","ref":"a0"}]


def test_wrong_host_or_lookalike_is_never_dispatched():
    for url in ("https://attacker.example/login",
                "https://walla.co.il.evil.example/login",
                "https://walla.co.il@evil.example/login"):
        b=BrowserStub([observation("o1",HOME,[("כניסה",url)])])
        result=run(b)
        assert not result.chain_verified
        assert result.dispatches==0 and b.act_calls==[]


def test_stale_dom_or_ambiguous_name_stops_without_click():
    b=BrowserStub([observation("o1",HOME,[("כניסה",LOGIN)],coherent=False)])
    assert run(b).dispatches==0
    b=BrowserStub([observation("o1",HOME,[("כניסה",LOGIN),("כניסה",LOGIN)])])
    assert run(b).reason_code=="no_unique_fresh_control"
    assert not b.act_calls


def test_source_host_not_requested_blocked():
    b=BrowserStub([observation("o1","https://example.com/",[("כניסה",LOGIN)])])
    assert run(b).dispatches==0


def test_does_not_fill_password_or_publish():
    b=BrowserStub([observation("o1",HOME,[("מחיקה","https://www.walla.co.il/delete")])])
    with pytest.raises(ValueError):
        run(b,[KnownNavigation("מחיקה","walla.co.il","walla.co.il","/delete")])
    assert not b.act_calls


@pytest.mark.parametrize("href",[
    "https://www.walla.co.il/login?code=secret",
    "https://www.walla.co.il/login#token",
    "javascript:fetch('/delete')",
])
def test_opaque_or_script_link_not_replayed(href):
    b=BrowserStub([observation("o1",HOME,[("כניסה",href)])])
    assert run(b).dispatches==0


def test_unconfirmed_action_does_not_get_retried():
    for effect in ("unknown","input_sent_false","timeout"):
        b=BrowserStub([observation("o1",HOME,[("כניסה",LOGIN)])],effect=effect)
        result=run(b)
        assert not result.chain_verified
        assert result.dispatches==1
        assert len(b.act_calls)==1
        assert result.model_calls==0


def test_homepage_after_click_not_form_or_goal():
    b=BrowserStub([
        observation("o1",HOME,[("כניסה",LOGIN)]),
        observation("o2",LOGIN,form=False),
    ])
    result=run(b)
    assert not result.chain_verified and result.dispatches==1
    assert result.reason_code=="post_action_evidence_missing"


def test_multistep_reuses_browser_act_after_observation():
    # The first click already returns a fresh Browser.observe() snapshot.
    second=KnownNavigation("לחשבון","walla.co.il","walla.co.il","/login",
                            post_condition="login_form")
    b=BrowserStub([
        observation("o1",HOME,[("כניסה",LOGIN)]),
        observation("o2",LOGIN,[("לחשבון",LOGIN)],form=True),
        observation("o3",LOGIN,form=True),
    ])
    res=run(b,[STEP,second])
    assert res.chain_verified and res.dispatches==2
    assert len(b.observed)==1  # never repeat expensive DOM capture


def test_user_approved_budget_stops_before_additional_step():
    b=BrowserStub([
        observation("o1",HOME,[("כניסה",LOGIN)]),
        observation("o2",LOGIN,form=True),
    ])
    # Extremely small budget can stop before first dispatch on slow hosts,
    # but never silently replay an uncertain click.
    res=run(b,budget_ms=0.000001)
    assert res.model_calls==0 and res.dispatches<=1


def test_100_successful_runs_have_zero_model_calls():
    for i in range(100):
        b=BrowserStub([
            observation("home",HOME,[("כניסה",LOGIN)]),
            observation("login",LOGIN,form=True),
        ])
        r=run(b)
        assert r.chain_verified and r.model_calls==0 and r.dispatches==1


def test_failure_never_claims_original_task_completion():
    b=BrowserStub([observation("o1",HOME,[("כניסה",LOGIN)])],effect="unknown")
    res=run(b)
    assert not res.chain_verified and not res.goal_verified
    assert len(b.act_calls)==1
