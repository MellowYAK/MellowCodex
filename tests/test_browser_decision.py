import asyncio
import json
from unittest.mock import AsyncMock, patch
import pytest
from hub.browser_decision import decision_context, decision_message
from hub.applications import Applications
from hub.errors import ObservationError
from hub.browser_workflow import disclosed_browser_tools

def page(title='דואר',stamp=100):
    return {'id':'read1','tool':'browser_observe','result':{
      'id':'obs1','url':'https://example.test/inbox?token=secret','title':title,
      'captured_at':stamp,'coherent':True,'page_signature':'p1','text':'Inbox',
      'headings':[{'text':title}],'elements':[{'ref':'e1','name':'סגור','enabled':True,'modal':True}]}}

@pytest.mark.parametrize('title',['תיבת דואר','Inbox','Входящие'])
def test_multilingual_page_and_modal_preserved(title):
    p=decision_context([page(title)],101)
    assert p['page']['title']==title
    assert p['visible_modal_controls'][0]['ref']=='e1'
    assert p['page']['fresh']

def test_stale_page_is_not_current():
    p=decision_context([page()],170)
    assert p['guidance_mode']=='refresh_stale_evidence'

def test_expected_outcome_not_promoted_to_fact():
    a={'id':'click1','tool':'browser_act','args':{'intent':'Open folder','expected_outcome':'File downloaded'},'result':{'input_sent':True,'dispatch_state':'dispatched'}}
    p=decision_context([page(),a],101)
    assert p['last_step']['expected_not_proven']=='File downloaded'
    assert 'verified' not in p['last_step']
    assert p['last_step']['source_action']=='click1'

def test_bounded_packet_and_no_source_mutation():
    a={'id':'click1','tool':'browser_act','args':{'intent':'x'*1000,'expected_outcome':'y'*1000},'result':{'input_sent':False,'error':'z'*1000}}
    actions=[page()]+[a]*20;before=json.dumps(actions)
    packet=decision_message(actions,101)
    assert packet and len(packet['content'])<=2400
    assert json.dumps(actions)==before

def test_unknown_effect_stays_unknown():
    a={'tool':'browser_act','result':{'input_sent':True,'dispatch_state':'unknown_effect'}}
    assert decision_context([page(),a],101)['unknown_effect']

def test_absent_observation_adds_no_packet():
    assert decision_message([]) is None

def test_browser_start_tools_remain_discoverable():
    names={'desktop_open','desktop_status','browser_navigate','tools_enable'}
    assert names<=disclosed_browser_tools(names,[])

def test_wrong_native_browser_is_preflight_not_uncertain_effect():
    app=Applications.__new__(Applications)
    app.find=AsyncMock(return_value={'windows':[],'installed':[]})
    with patch('hub.session.session_status',return_value={'interactive':True}),patch('hub.applications.subprocess.Popen') as launch:
        with pytest.raises(ObservationError,match='No input sent'):
            asyncio.run(app.open('Web workspace','https://example.test'))
        launch.assert_not_called()
