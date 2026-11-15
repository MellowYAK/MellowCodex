"""Browser.frame prefers native Qt capture, keeps fallback and geometry."""
import asyncio,base64,io,json,time
from types import SimpleNamespace
from unittest.mock import AsyncMock
from PIL import Image
from hub.browser import Browser,SNAPSHOT_JS


def png_data_uri(w=12,h=8):
    buf=io.BytesIO()
    Image.new("RGB",(w,h),(150,180,200)).save(buf,format="PNG")
    return "data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode()


def make_browser(monkeypatch,qt_success=True):
    b=Browser()
    b.target_id="qt-target"
    screenshot=AsyncMock(return_value=base64.b64decode(png_data_uri().split(",",1)[1]))
    calls=[]
    async def evaluate(expr,*args):
        if expr=="({width:innerWidth,height:innerHeight})":return {"width":12,"height":8}
        if expr==SNAPSHOT_JS:return {"elements":[{"ref":"e1","name":"Example","x":1,"y":2,"width":3,"height":4}]}
        if "Array.from" in expr:return []
        raise AssertionError("unexpected JS")
    page=SimpleNamespace(url="https://example.test/",screenshot=screenshot,
                         evaluate=evaluate,title=AsyncMock(return_value="Example"),
                         set_viewport_size=AsyncMock())
    async def connect():return page
    async def prepare(target):assert target=="qt-target"
    b.connect=connect;b.prepare_hidden_target=prepare
    class Process:
        returncode=0 if qt_success else 1
        async def communicate(self):
            if qt_success:
                return json.dumps({"image":png_data_uri(),"width":12,"height":8}).encode(),b""
            return b"",b"error"
    async def spawn(*argv,**kwargs):
        calls.append(argv)
        return Process()
    monkeypatch.setattr("hub.browser.asyncio.create_subprocess_exec",spawn)
    return b,page,calls


def test_native_qt_capture_first_avoids_playwright_font_timeout(monkeypatch):
    async def run():
        b,p,calls=make_browser(monkeypatch)
        p.screenshot.side_effect=AssertionError("Playwright screenshot should not run")
        frame=await b.frame()
        assert frame["url"]=="https://example.test/"
        assert frame["width"]==12 and frame["height"]==8
        assert len(frame["controls"])==1
        assert frame["image"].startswith("data:image/png;base64,")
        assert b.remote_frame["page"] is p
        assert any("--capture-target" in args for args in calls)
        p.screenshot.assert_not_awaited()
    asyncio.run(run())


def test_fallback_to_playwright_only_after_native_failure(monkeypatch):
    async def run():
        b,p,calls=make_browser(monkeypatch,False)
        frame=await b.frame()
        assert frame["url"]=="https://example.test/"
        assert frame["image"].startswith("data:image/jpeg;base64,")
        p.screenshot.assert_awaited_once()
    asyncio.run(run())
