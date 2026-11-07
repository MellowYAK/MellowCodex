from PIL import Image
from hub import screenshot_settings as ss

def test_compression_dimensions_format_and_original(tmp_path,monkeypatch):
    monkeypatch.setattr(ss,'STATE',tmp_path)
    original=tmp_path/'shot.png'
    Image.new('RGB',(3200,2000),'white').save(original)
    before=original.read_bytes()
    ss.save(ss.ScreenshotSettings(max_edge=1200,quality=65))
    result=ss.prepare(original)
    with Image.open(result) as image:
        assert image.format=='JPEG'
        assert image.size==(1200,750)
    assert original.read_bytes()==before
    assert ss.load().quality==65
    ss.save(ss.ScreenshotSettings(enabled=False))
    assert ss.prepare(original)==original
