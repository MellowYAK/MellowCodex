import pytest
from hub.ui_tars import parse_action,target_at,translate,call
from hub.errors import ObservationError
from hub.model_settings import ModelSettings,field_metadata
def page():
 return dict(id='o1',width=1000,height=500,elements=[dict(ref='e1',x=400,y=200,width=200,height=80,enabled=True,focused=True)])
def test_literal_parser():
 assert parse_action("Thought: Next\nAction: click(ref='e1')")==('click',{'ref':'e1'})
@pytest.mark.parametrize('text',["__import__('os').system('x')","click(ref=open('secret').read())","click(**{'ref':'e1'})","click(ref='e1'); evil()"])
def test_no_code_or_expansion(text):
 with pytest.raises(ObservationError):parse_action(text)
def test_scaled_coordinates():
 assert target_at(page(),'<point>250 120</point>',(500,250))=='e1'
@pytest.mark.parametrize('point',['9999 12','-1 2','nan 3','0 0'])
def test_reject_outside_or_unmapped(point):
 with pytest.raises(ObservationError):target_at(page(),point,(500,250))
def test_fresh_id_and_dom_ref():
 tool,args=translate('click',{'point':'250 120'},page(),(500,250))
 assert tool=='browser_act' and args==dict(observation_id='o1',action='click',ref='e1')
def test_focus_required():
 p=page();p['elements'][0]['focused']=False
 with pytest.raises(ObservationError):translate('type',{'content':'hi'},p,(500,250))
def test_no_unavailable_tools():
 with pytest.raises(ObservationError):call('run_shell',{'command':'x'},[])
def test_setting_default_and_validation():
 assert ModelSettings().browser_driver=='default'
 assert 'browser_driver' in field_metadata()
 with pytest.raises(ValueError):ModelSettings(browser_driver='unknown')
def test_no_finished_bypass():
 with pytest.raises(ObservationError):translate('finished',{'content':'success'},page(),(500,250))
