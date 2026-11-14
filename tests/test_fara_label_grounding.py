import pytest
from hub.fara import translate,controls
from hub.errors import ObservationError
def page():
 return {'id':'now','width':1000,'height':500,'elements':[{'ref':'cancel','name':'Back to safety','tag':'button','x':100,'y':200,'width':200,'height':50,'enabled':True},{'ref':'continue','name':'Continue','tag':'button','x':600,'y':200,'width':200,'height':50,'enabled':True}]}
def test_wrong_label_blocks_click():
 with pytest.raises(ObservationError):translate('click',{'point':'200 450','target_text':'Continue'},page(),(1000,500))
def test_correct_label_and_point():
 assert translate('click',{'point':'700 450','target_text':'Continue'},page(),(1000,500))[1]['ref']=='continue'
def test_controls_have_normalized_centers():
 assert controls(page())[1]=={'name':'Continue','center':[700,450]}
def test_back_uses_existing_guard():
 assert translate('history_back',{},page(),(1000,500))==('browser_act',{'observation_id':'now','action':'back'})

def test_nested_decorative_image_uses_actionable_parent():
 p=page();p['elements'].append({'ref':'icon','name':'','tag':'img','x':690,'y':215,'width':20,'height':20,'enabled':True})
 assert translate('click',{'point':'700 450','target_text':'Continue'},p,(1000,500))[1]['ref']=='continue'
