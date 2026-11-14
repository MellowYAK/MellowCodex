import copy
import json
import pytest
from hub.browser_evidence import compact_browser, display_url
from hub.model_context import build_packet

@pytest.mark.parametrize('target_index', [4, 5])
@pytest.mark.parametrize('reverse', [False, True])
def test_opaque_url_cannot_hide_entity(target_index, reverse):
    controls=[{'ref':'e'+str(i+1),'tag':'div','role':'link','name':'Entity '+str(i),'enabled':True} for i in range(9)]
    controls[0]={'ref':'e1','tag':'img','name':''}
    controls[target_index]['name']='Requested entity'
    if reverse: controls.reverse()
    raw={'id':'current','url':'https://identity.example/choose?state='+('opaque'*600)+'&code=PRIVATE_CODE','elements':controls,'text':'Choose an entity'}
    before=copy.deepcopy(raw)
    compact=compact_browser(raw,2500)
    assert any(e['name']=='Requested entity' for e in compact['elements'])
    assert 'PRIVATE_CODE' not in json.dumps(compact)
    assert raw==before
    messages=[{'role':'system','content':'Rules'},{'role':'user','content':'Choose Requested entity'},
              {'role':'assistant','tool_calls':[{'function':{'name':'browser_observe','arguments':{}}}]},
              {'role':'tool','tool_name':'browser_observe','content':json.dumps(raw)}]
    packet,diagnostic=build_packet(messages,[],16384,512,target_tokens=7000)
    observed=json.loads(next(m['content'] for m in packet if m['role']=='tool'))
    assert any(e['name']=='Requested entity' for e in observed['elements'])
    assert diagnostic['estimated_input']<=diagnostic['input_budget']

def test_url_summary_keeps_bounded_navigation_but_not_credentials():
    url='https://name:secret@example.test/items?page=2&tab=history&access_token=SECRET#access_token=SECRET'
    safe=display_url(url)
    assert 'page=2' in safe and 'tab=history' in safe
    assert 'secret' not in safe.lower() and 'name:' not in safe

def test_synthetic_history_optional_real_correction_and_latest_visual_mandatory():
    messages=[{'role':'system','content':'Rules'},{'role':'user','content':'Original objective'}]
    for i in range(18):
        messages.extend([
            {'role':'assistant','tool_calls':[{'function':{'name':'browser_observe','arguments':{}}}]},
            {'role':'tool','tool_name':'browser_observe','content':json.dumps({'id':str(i),'elements':[{'ref':'e1','name':'Next'}],'text':'Page '+str(i)})},
            {'role':'user','_evidence_kind':'screen','_evidence_observation':str(i),'content':'Prior OCR '+('obsolete '*500)}])
    correction={'role':'user','content':'CURRENT HUMAN CORRECTION: preserve existing records'}
    messages.insert(12,correction)
    messages[-1]['images']=['latest-image']
    original=copy.deepcopy(messages)
    packet,diag=build_packet(messages,[],32768,512,target_tokens=9000)
    assert correction in packet
    assert any(m.get('images')==['latest-image'] for m in packet)
    assert messages==original
    assert diag['omitted_message_count']>20
    assert all('_evidence_kind' not in m for m in packet)
    assert any(m.get('role')=='tool' and json.loads(m['content']).get('id')=='17' for m in packet)
