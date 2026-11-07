import pytest
from PIL import Image
from hub.capture_region import crop_capture

def test_region_preserves_original_and_negative_monitor_origin(tmp_path):
    path=tmp_path/'original.png';Image.new('RGB',(100,80),'red').save(path)
    shot={'id':'source','path':str(path),'left':-1680,'top':10,'width':100,'height':80}
    result=crop_capture(shot,[10,20,30,40])
    assert (result['left'],result['top'])==(-1670,30)
    assert Image.open(result['path']).size==(30,40)
    assert Image.open(path).size==(100,80)
    assert result['source_capture_id']=='source' and not result['input_ready']
    for region in ([-1,0,10,10],[0,0,101,1],[0,0,0,2],[0,0,1.2,3]):
        with pytest.raises(ValueError):crop_capture(shot,region)
