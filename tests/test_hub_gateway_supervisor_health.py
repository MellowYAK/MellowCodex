"""Guard control-plane startup must satisfy both managed health listeners.

The tests fake subprocess creation and never touch production ports/services.
"""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from hub.guardian.control_plane import Services


@pytest.mark.parametrize("relay_enabled", [False, True])
def test_supervisor_starts_hub_and_gateway_even_with_relay_enabled(tmp_path, monkeypatch, relay_enabled):
    state=tmp_path/"state";state.mkdir()
    (state/"relay.json").write_text(json.dumps({"enabled":relay_enabled}),encoding="utf-8")
    live=tmp_path/"live";live.mkdir()
    driver=Services({
        "root":str(tmp_path),
        "live":str(live),
        "python":"python-test-only",
        "ports":[8876,8897],
    })
    monkeypatch.setattr(driver,"owned",lambda:[])
    calls=[]
    class Process:
        def __init__(self,pid): self.pid=pid
        def create_time(self): return float(self.pid)
    def fake_popen(args,**kwargs):
        calls.append((args,kwargs))
        return SimpleNamespace(pid=10000+len(calls))
    monkeypatch.setattr("hub.guardian.control_plane.subprocess.Popen",fake_popen)
    monkeypatch.setattr("psutil.Process",lambda pid:Process(pid))
    driver.start()
    assert len(calls)==2
    assert calls[0][0][3]=="hub.app:app"
    assert calls[1][0][3]=="hub.mcp_gateway:app"
    assert driver.started==[(10001,10001.0),(10002,10002.0)]
    for args,kwargs in calls:
        assert kwargs["cwd"]==str(live)
        assert kwargs["env"]["LOCAL_AGENT_ROOT"]==str(tmp_path)
        assert kwargs["stdout"] is kwargs["stderr"]


def test_existing_owned_service_is_never_restarted(tmp_path,monkeypatch):
    live=tmp_path/"live";live.mkdir()
    driver=Services({"root":str(tmp_path),"live":str(live),"python":"python-test-only","ports":[8876,8897]})
    monkeypatch.setattr(driver,"owned",lambda:[object()])
    def forbidden(*a,**kw):raise AssertionError("must not start")
    monkeypatch.setattr("hub.guardian.control_plane.subprocess.Popen",forbidden)
    with pytest.raises(RuntimeError,match="Existing owned services"):
        driver.start()
