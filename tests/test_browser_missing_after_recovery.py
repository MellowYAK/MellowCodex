from hub.browser_workflow import pending_effect_guard

def history(signature='new',tab='tab',captured=2):
 before={'id':'before','coherent':True,'page_signature':'old','tab_id':'tab','frame_id':'main','captured_at':1}
 after={'id':'after','coherent':True,'page_signature':signature,'tab_id':tab,'frame_id':'main','captured_at':captured}
 return [{'tool':'browser_observe','result':before},{'id':'click','tool':'browser_act','args':{'action':'click','observation_id':'before'},'result':{'input_sent':True,'dispatch_state':'unknown_effect'}},{'tool':'browser_observe','result':after}]
def test_missing_after_can_reconcile_exact_origin_and_new_destination():
 assert pending_effect_guard(history()) is None
def test_same_page_still_blocks():
 assert pending_effect_guard(history(signature='old'))['retry_allowed'] is False
def test_other_tab_or_older_observation_cannot_clear():
 assert pending_effect_guard(history(tab='unrelated'))
 assert pending_effect_guard(history(captured=0))
def test_unknown_origin_stays_blocked():
 rows=history();rows[1]['args']['observation_id']='unknown'
 assert pending_effect_guard(rows)
