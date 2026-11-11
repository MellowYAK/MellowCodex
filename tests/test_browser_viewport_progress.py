import asyncio
from types import SimpleNamespace
from hub.browser import Browser
from hub.browser_workflow import pending_effect_guard,completion_check,requires_outcome,verify_outcome_freshness

def test_scroll_is_observation_not_business_mutation():
 scroll={'tool':'browser_act','args':{'action':'scroll'},'result':{'input_sent':True,'dispatch_state':'dispatched_pending'}}
 assert not requires_outcome(scroll)
 assert pending_effect_guard([scroll]) is None
 assert completion_check([scroll]) is None
 assert not verify_outcome_freshness({}, {'status':'success','verified':True}, [scroll])['verified']
 click={'tool':'browser_act','args':{'action':'click'},'result':{'input_sent':True,'dispatch_state':'dispatched_pending'}}
 assert requires_outcome(click)
 assert pending_effect_guard([click]) is not None
 assert completion_check([click]) is False

def test_scroll_does_not_clear_earlier_uncertain_write():
 click={'id':'write','tool':'browser_act','args':{'action':'click'},'result':{'input_sent':True,'dispatch_state':'unknown_effect'}}
 scroll={'tool':'browser_act','args':{'action':'scroll'},'result':{'input_sent':True}}
 assert pending_effect_guard([click,scroll])['pending_action_id']=='write'

def test_scroll_transition_is_detected():
 async def run():
  b=Browser();before={'url':'same','ready':'complete','viewport':{'y':0}}
  async def probe(page):return dict(before,viewport={'y':600})
  b.transition_state=probe
  result=await b.settle_transition(SimpleNamespace(),before,[],timeout=1)
  assert result['state']=='observed_transition'
 asyncio.run(run())

def test_dom_probe_includes_real_viewport_position():
 async def run():
  class Page:
   async def evaluate(self,script):
    assert 'x:scrollX,y:scrollY' in script
    return {'viewport':{'x':0,'y':600}}
  assert (await Browser().transition_state(Page()))['viewport']['y']==600
 asyncio.run(run())
