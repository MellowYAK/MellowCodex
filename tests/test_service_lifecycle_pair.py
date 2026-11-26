from unittest.mock import patch
from pathlib import Path
import pytest
from hub import service_health as h

@pytest.mark.parametrize("service",["hub","gateway"])
@pytest.mark.parametrize("action",["Start","Stop","Restart"])
def test_pair_targets(service,action):
    assert h.lifecycle_targets(action,service)==["hub","gateway"]

def test_mcp_stop_preserves_hub_but_restart_drains_pair():
    assert "hub" not in h.lifecycle_targets("Stop","mcp")
    assert h.lifecycle_targets("Restart","mcp")[:2]==["hub","gateway"]

@pytest.mark.parametrize("service",["hub","gateway","mcp"])
def test_restart_refuses_busy_before_any_mutation(service):
    with patch.object(h,"active_tasks",return_value=[{"id":"active"}]),patch.object(h,"inventory") as inv:
        with pytest.raises(RuntimeError,match="Active tasks"):
            h.preflight("Restart",service)
        inv.assert_not_called()

def test_restart_gateway_checks_both_owned_ports():
    with patch.object(h,"active_tasks",return_value=[]),patch.object(h,"config",return_value={}),patch.object(h,"inventory",return_value={"hub":[{"pid":1,"owned":True}],"gateway":[{"pid":2,"owned":True}]}),patch.object(h,"port_identity",side_effect=[(True,{99}),(True,{2})]):
        with pytest.raises(RuntimeError,match="ownership"):
            h.preflight("Restart","gateway")

def test_pair_restart_requires_guard_and_both_healthy():
    rows=[{"id":k,"owned":True,"http_status":200} for k in ("hub","gateway")]
    with pytest.raises(RuntimeError,match="Guard-owned"):
        h.verify_result("Restart","hub",{"services":rows})
    receipt={"services":rows,"guard_supervisor":{"supervisor_healthy":True}}
    h.verify_result("Restart","gateway",receipt)
    rows[1]["http_status"]=503
    with pytest.raises(RuntimeError,match="gateway"):
        h.verify_result("Restart","hub",receipt)

def test_controller_source_routes_pair_through_graceful_drain_and_guard():
    root=Path(__file__).resolve().parents[1]
    stop=(root/"scripts/stop-mcp-transports.py").read_text(encoding="utf8")
    ps=(root/"reconcile-services.ps1").read_text(encoding="utf8")
    assert "if pair:" in stop
    assert stop.index("if code==200:quiesce()") < stop.index("def stop_tree")
    assert "Unexpected child; refusing stop" in stop
    assert "('hub','gateway','all')" in stop
    assert "@('Start','Restart','Reconcile')" in ps
    assert "--restart-pair" in ps
    assert "legacy launch forbidden" in ps
