import pytest
from hub.browser_workflow import pending_effect_guard, verify_outcome_freshness, assess
@pytest.mark.parametrize('repeat',range(3))
def test_uncertain_effect_is_not_replayed_after_blocked_attempt(repeat):
 pending={'id':'uncertain','tool':'browser_act','result':{'input_sent':True,'dispatch_state':'dispatched_pending','after':{'page_signature':'same'}}}
 blocked={'tool':'browser_act','result':{'input_sent':False,'dispatch_state':'not_dispatched'}}
 observation={'tool':'browser_observe','result':{'id':'fresh','elements':[],'coherent':True,'page_signature':'same'}}
 actions=[pending,blocked,observation,{'tool':'browser_act','result':None,'state':'pending'}]
 assert pending_effect_guard(actions)['pending_action_id']=='uncertain'
 observation['result']['page_signature']='changed'
 assert pending_effect_guard(actions) is None

def test_existing_success_text_does_not_prove_fresh_operation():
 old={'id':'before','elements':[],'text':'Channel connected successfully'}
 page=dict(old,id='after')
 actions=[{'tool':'browser_observe','result':old},{'tool':'browser_act','result':{'input_sent':True}}]
 args={'status':'success','evidence':old['text'],'reason':'existing label'}
 result=verify_outcome_freshness(page,assess(page,args),actions)
 assert not result['verified'] and result['fresh_operation_verified'] is False
 page['text']='Channel updated successfully at revision 22'
 args['evidence']=page['text']
 result=verify_outcome_freshness(page,assess(page,args),actions)
 assert result['verified'] and result['fresh_operation_verified']

def test_quote_and_interpretation_are_separate():
 from hub.errors import ObservationError
 page={'id':'observed','elements':[],'text':'Connection saved successfully'}
 with pytest.raises(ObservationError,match='interpretation'):
  assess(page,{'status':'success','evidence':page['text']+' (this proves it)','reason':''})
 with pytest.raises(ObservationError):
  assess(page,{'status':'success','evidence':'Fabricated connection success','reason':''})

def test_unchanged_reads_have_bounded_polling_and_reset_on_input():
 from hub.browser_workflow import repeated_browser_reads
 read={'tool':'browser_observe','args':{},'state':'complete','result':{'page_signature':'same'}}
 assert not repeated_browser_reads('browser_observe',{},[read,read])
 assert repeated_browser_reads('browser_observe',{},[read,read,read])
 assert not repeated_browser_reads('browser_observe',{'query':'new'},[read,read,read])
 mutation={'tool':'browser_act','result':{'input_sent':True}}
 assert not repeated_browser_reads('browser_observe',{},[read,read,read,mutation])
