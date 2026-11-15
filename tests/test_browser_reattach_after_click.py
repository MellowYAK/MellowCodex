"""Regression: native Qt click requires a new Playwright transport on next read."""
import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock
from hub.browser import Browser


def test_native_click_marks_transport_for_next_reconnect(monkeypatch):
    async def run():
        b=Browser();b.target_id="native"
        page=SimpleNamespace(url="https://example.test/")
        async def connect():return page
        b.connect=connect
        b.remote_frame={"id":"f","page":page,"url":page.url,
                        "at":time.monotonic(),"width":400,"height":300}
        class Process:
            async def communicate(self):
                return b'{"input_sent":true,"backend":"qt-widget-events"}',b""
        async def spawn(*args,**kwargs):return Process()
        monkeypatch.setattr("hub.browser.asyncio.create_subprocess_exec",spawn)
        result=await b.remote_input({"frame_id":"f","action":"click","x":30,"y":25})
        assert result["input_sent"] is True
        assert b.reattach_after_native_input is True
        assert b.remote_frame is None
    asyncio.run(run())


def test_browser_reconnect_state_is_initially_false():
    assert Browser().reattach_after_native_input is False
