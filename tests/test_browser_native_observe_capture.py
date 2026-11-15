"""Native Qt screenshot should be first on browser observation, without losing ref/coherence checks."""
import asyncio,base64,io,json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from PIL import Image
from hub.browser import Browser,SNAPSHOT_JS


def make_uri():
    buffer=io.BytesIO()
    Image.new("RGB",(24,16),(30,110,200)).save(buffer,format="JPEG")
    return "data:image/jpeg;base64,"+base64.b64encode(buffer.getvalue()).decode()


def test_observe_uses_native_capture_without_playwright_timeout(monkeypatch,tmp_path):
    async def run():
        browser=Browser()
        browser.target_id="target-1"
        async def connect():return page
        browser.connect=connect
        async def signature(page):return "stable"
        browser.semantic_signature=signature
        async def evaluate(js,*args):
            assert js==SNAPSHOT_JS
            return {"url":"https://example.test","title":"Test","text":"A label",
                    "elements":[{"ref":"e1","name":"A label","enabled":True,"tag":"button"}],
                    "links":[],"notices":[]}
        page=SimpleNamespace(url="https://example.test",evaluate=evaluate,
                             screenshot=AsyncMock(side_effect=AssertionError("Do not call Playwright")))
        class Process:
            returncode=0
            async def communicate(self):
                return json.dumps({"image":make_uri(),"width":24,"height":16}).encode(),b""
        async def spawn(*args,**kwargs):
            assert "--capture-target" in args
            return Process()
        monkeypatch.setattr("hub.browser.asyncio.create_subprocess_exec",spawn)
        result=await browser.observe(tmp_path)
        assert result["coherent"] is True
        assert result["screenshot_observation_id"]==result["id"]
        assert result["capture_backend"]=="qt-native"
        assert len(result["elements"])==1
        assert Path(result["path"]).is_file()
        with Image.open(result["path"]) as photo:assert photo.size==(24,16)
        page.screenshot.assert_not_awaited()
    asyncio.run(run())


def test_observe_fallback_keeps_existing_playwright_path(monkeypatch,tmp_path):
    async def run():
        browser=Browser()
        browser.target_id="target-1"
        async def connect():return page
        browser.connect=connect
        async def signature(page):return "same"
        browser.semantic_signature=signature
        async def evaluate(js,*args):
            return {"url":"https://example.test","title":"Example","text":"Example",
                    "elements":[],"links":[],"notices":[]}
        async def playwright_shot(path,timeout):
            Image.new("RGB",(24,16),(20,30,40)).save(path,format="PNG")
        page=SimpleNamespace(url="https://example.test",evaluate=evaluate,
                             screenshot=AsyncMock(side_effect=playwright_shot))
        class Process:
            returncode=1
            async def communicate(self):return b"",b"native unavailable"
        async def spawn(*args,**kwargs):return Process()
        monkeypatch.setattr("hub.browser.asyncio.create_subprocess_exec",spawn)
        result=await browser.observe(tmp_path)
        assert result["capture_backend"]=="playwright-fallback"
        assert result["screenshot_observation_id"]==result["id"]
        page.screenshot.assert_awaited_once()
    asyncio.run(run())
