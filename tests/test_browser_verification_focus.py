from hub.browser_workflow import verification_focus
def rejected():
 return {'tool':'browser_assess','result':{'verified':False,'fresh_operation_verified':True,'entity_verified':False,'evidence':'Alex joined Workspace successfully'}}
def test_focus_requires_proven_operation_not_intermediate_or_uncertain():
 assert not verification_focus([])
 assert not verification_focus([{'tool':'browser_assess','result':{'verified':False}}])
 assert verification_focus([rejected()])
def test_focus_ends_on_new_action_navigation_or_verification():
 for a in [{'tool':'browser_act','result':{}},{'tool':'browser_navigate','result':{}},{'tool':'browser_assess','result':{'verified':True}}]:
  assert not verification_focus([rejected(),a])
def test_same_page_refresh_preserves_focus_changed_page_drops_it():
 obs={'tool':'browser_observe','result':{'id':'new','elements':[],'text':'Alex joined Workspace successfully'}}
 assert verification_focus([rejected(),obs])
 obs['result']['text']='Another page'
 assert not verification_focus([rejected(),obs])
