from test_ui_tars import *

def test_native_coordinates_in_ref_normalized():
 tool,args=translate('click',{'ref':'(250,120)'},page(),(500,250))
 assert args['ref']=='e1'
def test_invented_ref_rejected_before_dispatch():
 with pytest.raises(ObservationError):translate('click',{'ref':'invented'},page(),(500,250))
