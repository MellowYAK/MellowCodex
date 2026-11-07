import json
from hub.development.memory import packet


def action(name,result,args=None):return {'tool':name,'state':'complete','args':args or {},'result':result}


def test_pinned_memory_keeps_candidate_revision_and_does_not_claim_activation():
    actions=[action('candidate_create',{'id':'candidate','revision':0}),action('candidate_repair',{'candidate_id':'candidate','revision':1,'test':{'verified':True}}),action('upgrade_activate',{'id':'request','state':'running'})]
    result=packet(actions)
    assert '"revision": 1' in result and '"tests_verified": true' in result
    assert '"activation_verified": false' in result


def test_repeated_observations_are_detected_without_changing_durable_data():
    actions=[action('project_index_status',{'state':'not_indexed'}) for _ in range(4)]
    before=json.dumps(actions)
    assert '"count": 4' in packet(actions)
    assert json.dumps(actions)==before
