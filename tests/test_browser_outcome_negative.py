import time
from hub.browser_workflow import assess,completion_check
def test_negated_success_is_not_success():
    page={'id':'o','text':'Channel Comics is not connected','notices':[],'elements':[]}
    assert assess(page,{'status':'success','evidence':page['text'],'reason':'verify requested channel'})['verified'] is False
def test_navigation_after_receipt_invalidates_completion():
    actions=[{'tool':'browser_act'},{'tool':'browser_assess','result':{'status':'success','verified':True,'checked_at':time.time()}},{'tool':'browser_navigate','result':{'url':'https://example.test/other'}}]
    assert completion_check(actions) is False
