import pytest
from hub.fara import translate,controls
from hub.errors import ObservationError

def page():
 return {'id':'now','width':1000,'height':500,'elements':[{'ref':'social','name':'↗\nСоциальные сети','tag':'button','x':0,'y':0,'width':200,'height':100,'enabled':True}]}
def test_decorative_prefix_keeps_named_control_actionable():
 assert translate('click',{'point':'100 100','target_text':'Социальные сети'},page(),(1000,500))[1]['ref']=='social'
 assert controls(page())[0]['name']=='Социальные сети'
def test_different_meaning_still_blocks():
 with pytest.raises(ObservationError):translate('click',{'point':'100 100','target_text':'Continue'},page(),(1000,500))
