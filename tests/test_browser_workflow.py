import time
from hub.browser_workflow import assess,completion_check,retry_guard
from hub.errors import ObservationError
import pytest

def page(text):
 return {'id':'observed','text':text,'notices':[],'elements':[{'ref':'e1','name':'Try again','enabled':True}]}

def test_failure_safe_retry_and_bound():
 p=page('Connection failed. No channel was linked.')
 r=assess(p,{'status':'failure','evidence':'Connection failed.','reason':'Explicitly no link was created.'})
 assert r['retry_allowed'] and not r['verified']
 p['assessment']=r;retry_guard(p,'e1')
 with pytest.raises(ObservationError):retry_guard(p,'e2')
 assert not assess(p,{'status':'failure','evidence':'Connection failed.','reason':'retry'},2)['retry_allowed']

def test_ambiguous_effect_never_replayed():
 p=page('Connection failed. Outcome unknown.')
 assert not assess(p,{'status':'failure','evidence':'Connection failed.','reason':'Maybe retry'})['retry_allowed']
 with pytest.raises(ObservationError):retry_guard(p,'e1')

def test_success_requires_observed_terminal_evidence():
 p=page('Account selected. Continue.')
 assert not assess(p,{'status':'success','evidence':'Account selected.'})['verified']
 with pytest.raises(ObservationError):assess(p,{'status':'success','evidence':'Channel connected successfully.'})
 p=page('Channel demo connected successfully.')
 assert assess(p,{'status':'success','evidence':p['text']})['verified']

def test_failure_cannot_be_labelled_success():
 p=page('Connection failed. Previously connected channel remains.')
 assert not assess(p,{'status':'success','evidence':'Previously connected channel remains.'})['verified']

def test_final_gate_binds_to_last_effect_and_expires():
 action={'tool':'browser_act','result':{'input_sent':True}}
 receipt={'tool':'browser_assess','result':{'status':'success','verified':True,'checked_at':time.time()}}
 assert completion_check([action]) is False
 assert completion_check([action,receipt]) is True
 assert completion_check([action,receipt,action]) is False
 receipt['result']['checked_at']-=121
 assert completion_check([action,receipt]) is False
