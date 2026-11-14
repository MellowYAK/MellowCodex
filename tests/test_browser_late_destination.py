from hub.browser_workflow import pending_effect_guard,completion_check

def history(after_signature='new',after_time=2):
 before={'id':'before','coherent':True,'page_signature':'old','tab_id':'tab','frame_id':'main','captured_at':1,'elements':[]}
 after={'id':'after','coherent':True,'page_signature':after_signature,'tab_id':'tab','frame_id':'main','captured_at':after_time,'elements':[]}
 return [{'tool':'browser_observe','result':before},{'id':'click','tool':'browser_act','args':{'action':'click','observation_id':'before'},'result':{'input_sent':True,'dispatch_state':'dispatched_pending','after':after}}]
def test_late_after_is_compared_to_before_not_to_itself():
 rows=history();assert pending_effect_guard(rows) is None
 assert completion_check(rows) is False
 rows.append({'tool':'browser_observe','result':rows[-1]['result']['after']})
 assert pending_effect_guard(rows) is None
def test_unchanged_or_older_after_does_not_clear_uncertainty():
 assert pending_effect_guard(history('old'))
 assert pending_effect_guard(history(after_time=0))
