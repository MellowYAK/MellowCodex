"""Qt WebEngine browser scrolling avoids the crashing CDP wheel path."""
import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock
from hub.browser import Browser


def test_virtual_scroll_uses_dom_not_cdp_wheel():
    async def run():
        wheel=AsyncMock(side_effect=AssertionError("Qt CDP mouse.wheel must not be called"))
        evaluator=AsyncMock(return_value={"before":0,"after":320})
        page=SimpleNamespace(url="https://example.test/",mouse=SimpleNamespace(wheel=wheel),evaluate=evaluator)
        browser=Browser()
        async def connect():return page
        browser.connect=connect
        browser.remote_frame={"id":"frame","page":page,"url":page.url,
                              "at":time.monotonic(),"width":650,"height":420}
        result=await browser.remote_input({"frame_id":"frame","action":"scroll","amount":320})
        assert result["input_sent"] is True
        assert result["backend"]=="embedded-browser-dom-scroll"
        assert result["scroll_changed"] is True
        assert result["scroll_y_after"]==320
        assert result["physical_pointer_used"] is False
        assert browser.remote_frame is None
        assert evaluator.await_args.args[1]==320
        wheel.assert_not_awaited()
    asyncio.run(run())


def test_virtual_scroll_is_clamped_and_never_claims_change_at_bottom():
    async def run():
        page=SimpleNamespace(url="https://example.test/",evaluate=AsyncMock(return_value={"before":10,"after":10}))
        browser=Browser()
        async def connect():return page
        browser.connect=connect
        browser.remote_frame={"id":"frame","page":page,"url":page.url,
                              "at":time.monotonic(),"width":400,"height":300}
        result=await browser.remote_input({"frame_id":"frame","action":"scroll","amount":90000})
        assert page.evaluate.await_args.args[1]==2000
        assert result["input_sent"] is True
        assert result["scroll_changed"] is False
        assert browser.remote_frame is None
    asyncio.run(run())


def test_virtual_scroll_rejects_stale_before_input():
    async def run():
        page=SimpleNamespace(url="https://example.test/",evaluate=AsyncMock())
        browser=Browser()
        async def connect():return page
        browser.connect=connect
        browser.remote_frame={"id":"frame","page":page,"url":page.url,
                              "at":time.monotonic()-17,"width":400,"height":300}
        from hub.errors import ObservationError
        try:
            await browser.remote_input({"frame_id":"frame","action":"scroll","amount":250})
        except ObservationError:pass
        else:raise AssertionError("stale frame must be rejected")
        page.evaluate.assert_not_awaited()
    asyncio.run(run())
