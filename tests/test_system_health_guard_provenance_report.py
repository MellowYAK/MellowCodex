"""Guard supervision provenance and diagnostic coverage are visible in text status."""
from hub.system_health import format_report
import time

def sample(supervisor):
    return {
        "checked_at":time.time(),
        "overall_status":"operational",
        "services":[{"id":"hub","name":"Hub","status":"operational",
                     "checked_at":time.time(),"reason":"MCP operational"}],
        "network":{"state":"error","reason":"Public HTTP 503; authenticated MCP works"},
        "guard_supervisor":supervisor,
        "diagnostic_coverage":{"status":"degraded","reason":"Independent public /health failed"},
        "connectors":{}}

def test_observed_hub_healthy_but_guard_start_not_proven():
    report=format_report(sample({
        "state":"verified","healthy":True,"supervisor_healthy":False,
        "observed_healthy":True,"health_basis":"verified_existing_services"}))
    assert "תקינות תהליכים נצפית: אומתה" in report
    assert "הפעלה בבעלות Guard: לא אומתה" in report
    assert "כיסוי אבחון: מוגבל" in report
    assert "מצב השירותים המקומיים: תקין" in report

def test_guard_probe_failure_does_not_become_service_outage():
    report=format_report(sample({"state":"unknown",
                                 "reason":"Guard authenticated status unavailable: ExceptionGroup"}))
    assert "בדיקת Guard עצמאית: לא אומתה" in report
    assert "ExceptionGroup" in report
    assert "Hub: תקין" in report
