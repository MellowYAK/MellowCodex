from hub.browser_workflow import completion_check

def test_rejected_existing_status_cannot_complete_new_change():
    read={'tool':'browser_observe','result':{'text':'Old successful receipt'}}
    rejected={'tool':'browser_assess','result':{'status':'success','verified':False,'next_step':'No operation evidence in this task'}}
    assert completion_check([read]) is None
    assert completion_check([read,rejected]) is False

def test_assessment_without_operation_cannot_prove_new_effect():
    assert completion_check([{'tool':'browser_assess','result':{'status':'success','verified':True}}]) is False
