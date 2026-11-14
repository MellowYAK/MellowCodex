from copy import deepcopy
from hub.browser_workflow import assessment_entities,assessment_catalog,repeated_assessment
def actions():
 return [{'tool':'browser_act','result':{'input_sent':True,'target':{'name':'Alex Example'}}}]
def test_entities_require_observed_input_goal_and_evidence():
 a=actions()
 assert assessment_entities('Set up Alex Example','Alex Example completed successfully',a)==['Alex Example']
 assert not assessment_entities('Set up Someone Else','Alex Example completed successfully',a)
 assert not assessment_entities('Set up Alex Example','Receipt abcdef',a)
 a[0]['result']['input_sent']=False
 assert not assessment_entities('Alex Example','Alex Example',a)
def test_catalog_choices_are_task_bound_and_do_not_mutate_global_schema():
 from hub.tools import CATALOG
 original=deepcopy(CATALOG)
 a=actions()+[{'tool':'browser_observe','result':{'id':'p','elements':[],'text':'Alex Example completed successfully'}}]
 c=assessment_catalog(CATALOG,'Set up Alex Example',a)
 tool=next(x for x in c if x['function']['name']=='browser_assess')
 assert tool['function']['parameters']['properties']['entity']['enum']==['Alex Example']
 assert CATALOG==original
def test_identical_rejections_bounded_without_blocking_corrected_entity():
 args={'entity':'wrong','evidence':'Exact quote'}
 a={'tool':'browser_assess','args':args,'result':{'verified':False}}
 assert repeated_assessment('browser_assess',args,[a,a,a])
 assert not repeated_assessment('browser_assess',dict(args,entity='correct'),[a,a,a])
