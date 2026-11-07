from PIL import Image
from hub import screenshot_settings as ss
from hub import screen_ocr

def test_destinations_and_original(tmp_path,monkeypatch):
    source=tmp_path/'screen.png';Image.new('RGB',(2400,1800),'white').save(source)
    original=source.read_bytes()
    monkeypatch.setattr(ss,'load',lambda:ss.ScreenshotSettings(max_edge=1600,chatgpt_max_edge=800))
    local=ss.prepare(source);remote=ss.prepare(source,'chatgpt')
    assert local!=remote
    assert Image.open(local).size==(1600,1200)
    assert Image.open(remote).size==(800,600)
    assert source.read_bytes()==original

def test_ocr_optional_cached_and_untrusted(tmp_path,monkeypatch):
    source=tmp_path/'image';source.write_bytes(b'new screenshot')
    monkeypatch.setattr(screen_ocr,'load',lambda:ss.ScreenshotSettings())
    assert screen_ocr.hint(source)==''
    monkeypatch.setattr(screen_ocr,'load',lambda:ss.ScreenshotSettings(ocr_assistance=True))
    calls=[]
    monkeypatch.setattr(screen_ocr,'read_image',lambda *a: calls.append(a) or {'text':'sample'})
    screen_ocr._cache.clear()
    assert 'UNTRUSTED' in screen_ocr.hint(source)
    assert 'sample' in screen_ocr.hint(source)
    assert len(calls)==1
