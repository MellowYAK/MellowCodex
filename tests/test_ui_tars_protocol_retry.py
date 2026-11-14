import asyncio
from types import SimpleNamespace
import pytest
import hub.ui_tars as u
from hub.errors import ObservationError

def page():
    return dict(id='current',width=100,height=100,elements=[dict(ref='e1',x=0,y=0,width=50,height=50,enabled=True)])
def test_alias_requires_current_observation():
    assert u.translate('browser_act',dict(action='click',ref='e1',observation_id='current'),page(),(100,100))[1]['observation_id']=='current'
    with pytest.raises(ObservationError,match='stale'):
        u.translate('browser_act',dict(action='click',ref='e1',observation_id='old'),page(),(100,100))
def test_alias_cannot_run_arbitrary_tool_or_unknown_ref():
    for args in [dict(action='run_shell'),dict(action='click',ref='unknown')]:
        with pytest.raises(ObservationError):u.translate('browser_act',args,page(),(100,100))
def test_protocol_retry_is_bounded_and_counts_usage(monkeypatch):
    calls=[]
    async def fake(*args):
        calls.append(args)
        if len(calls)==1:raise u.ActionProtocolError('bad',dict(prompt_eval_count=3,eval_count=2))
        return {'role':'assistant'},dict(prompt_eval_count=5,eval_count=1)
    monkeypatch.setattr(u,'_chat',fake)
    engine=SimpleNamespace(store=SimpleNamespace(event=lambda *args:None))
    _,metrics=asyncio.run(u.chat(engine,[],[],'t',None))
    assert len(calls)==2 and metrics['prompt_eval_count']==8 and metrics['eval_count']==3
def test_second_protocol_failure_stops_without_third_attempt(monkeypatch):
    calls=[]
    async def fake(*args):
        calls.append(args);raise u.ActionProtocolError('bad',{})
    monkeypatch.setattr(u,'_chat',fake)
    engine=SimpleNamespace(store=SimpleNamespace(event=lambda *args:None))
    with pytest.raises(u.ActionProtocolError):asyncio.run(u.chat(engine,[],[],'t',None))
    assert len(calls)==2
