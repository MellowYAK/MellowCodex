from hub.browser_workflow import disclosed_browser_tools
NAMES={'browser_act','browser_assess','browser_observe','tools_enable','computer_power_status'}
def page(text='Agreement',age=0,coherent=True):
 return {'tool':'browser_observe','result':{'id':'p','captured_at':100-age,'coherent':coherent,'page_signature':'same','text':text,'elements':[{'ref':'e1','tag':'button','enabled':True,'name':'Continue'}]}}
def test_intermediate_disclosure_preserves_action_and_discovery():
 n=disclosed_browser_tools(NAMES,[page()],100)
 assert 'browser_assess' not in n and {'browser_act','browser_observe','tools_enable'}<=n
def test_stale_uncertain_and_pending_keep_observation_and_assessment():
 for a in [page(age=61),page(coherent=False)]:
  assert {'browser_observe','browser_assess'}<=disclosed_browser_tools(NAMES,[a,a],100)
 pending={'tool':'browser_act','result':{'input_sent':True,'dispatch_state':'unknown_effect'}}
 assert {'browser_observe','browser_assess'}<=disclosed_browser_tools(NAMES,[pending,page(),page()],100)
def test_redundant_reads_are_hidden_only_while_fresh():
 assert 'browser_observe' not in disclosed_browser_tools(NAMES,[page(),page()],100)
 assert 'browser_observe' in disclosed_browser_tools(NAMES,[page(),page()],161)
def test_terminal_evidence_keeps_assessment_across_languages():
 for text in ['Completed successfully','\u05d4\u05d5\u05e9\u05dc\u05dd \u05d1\u05d4\u05e6\u05dc\u05d7\u05d4','\u0443\u0441\u043f\u0435\u0448\u043d\u043e']:
  assert 'browser_assess' in disclosed_browser_tools(NAMES,[page(text)],100)
