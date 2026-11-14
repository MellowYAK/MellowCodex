import json
import pytest
from hub.browser_evidence import resolve_ref
from hub.errors import ObservationError
from hub.model_context import compact_result

def test_unique_observed_name_only():
    obs={'refs':{'e1','e2'},'elements':[{'ref':'e1','name':'Connect'},{'ref':'e2','name':'Other'}]}
    assert resolve_ref(obs,'e1')=='e1'
    assert resolve_ref(obs,'Connect')=='e1'
    for bad in ('connect','Connec','invented',None):
        with pytest.raises(ObservationError):resolve_ref(obs,bad)
    obs['elements'][1]['name']='Connect'
    with pytest.raises(ObservationError,match='Ambiguous'):resolve_ref(obs,'Connect')

def test_controls_survive_large_offscreen_prose():
    elements=[{'ref':f'e{i}','tag':'button','name':f'Control {i}','x':30,'width':200} for i in range(1,31)]
    value={'id':'fresh','url':'https://example.test','text':'irrelevant '*5000,'elements':elements}
    result=json.loads(compact_result(value))
    assert result['id']=='fresh'
    assert [e['ref'] for e in result['elements']]==[e['ref'] for e in elements]
    assert result['elements_omitted']==0
    assert result['text_truncated']
    assert len(compact_result(value))<7000

def test_dense_controls_report_omissions_and_query():
    value={'id':'fresh','elements':[{'ref':f'e{i}','tag':'button','name':'Long control '+str(i)*30} for i in range(200)]}
    result=json.loads(compact_result(value,1500))
    assert result['elements_omitted']>0
    assert result['element_count']==200
    assert 'query' in result['action_hint']
    assert len(compact_result(value,1500))<1500

def test_after_action_preserves_input_and_control_identity():
    value={'action':'click','input_sent':True,'after':{'id':'next','elements':[{'ref':'e2','name':'Continue','tag':'button'}],'text':'x'*40000}}
    result=json.loads(compact_result(value))
    assert result['input_sent'] is True
    assert result['after']['id']=='next'
    assert result['after']['elements'][0]['ref']=='e2'
