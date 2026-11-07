from hub.action_log import action_log
from hub.store import Store

def test_log_distinguishes_returned_verified_and_failed(tmp_path):
    store=Store(tmp_path/'log.db');task=store.create('goal',str(tmp_path),'desktop','log')
    for tool,result in [('click',{'input_sent':True}),('read',{'text_verified':False}),('alternate',{'text_verified':True}),('shell',{'exit_code':1,'stderr':'denied'})]:
        action=store.begin_action(task['id'],tool,{'test':True});store.end_action(action,result)
    log=action_log(store,task['id'])
    assert [r['outcome'] for r in log['actions']]==['returned_unverified','verification_failed','verified','failed']
    assert log['actions'][2]['different_tool_after_failure']
    assert log['actions'][2]['follows_failure']==log['actions'][1]['action_id']
    assert log['actions'][3]['result']['stderr']=='denied'
