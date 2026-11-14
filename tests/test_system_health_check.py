"""Focused deterministic system-status regressions."""
import time
from hub import system_health


def test_status_aliases_without_model():
    for phrase in (
        "סטטוס", "בדוק את כל השירותים", "בדיקת בריאות",
        "status", "System Health", "Check all services",
        "СТАТУС", "Проверь сервисы", "estado del sistema",
    ):
        assert system_health.is_status_request(phrase), phrase
    for phrase in (
        "status of task 123", "how to add a status button",
        "פתח אתר סטטוס של ספק", "connect the YouTube channel",
        "Проверь загрузку видео", "",
    ):
        assert not system_health.is_status_request(phrase), phrase


def test_report_has_independent_service_states_and_times():
    stamp=time.time()
    data={"checked_at":stamp,"local_overall_status":"operational","services":[
        {"id":"hub","name":"Hub","status":"operational","reason":"API 200","checked_at":stamp},
        {"id":"model","name":"Model","status":"intentionally_stopped","reason":"unloaded intentionally","checked_at":stamp},
        {"id":"guard","name":"Guard","status":"unverified","reason":"Probe raised TimeoutError","checked_at":stamp}],
        "network":{"state":"available","reason":"IPv6 available"},
        "connectors":{"mellowcodex":{"status":"operational","reason":"authenticated MCP response","checked_at":stamp,"last_success_at":stamp}}}
    report=system_health.format_report(data)
    assert "Hub: תקין" in report
    assert "Model: הופסק בכוונה" in report
    assert "Guard: אימות לא הושלם" in report
    assert "SSH" in report
    assert "authenticated MCP response" in report
    assert "API 200" in report


def test_checked_report_never_mislabels_probe_exception(monkeypatch):
    from hub import service_health
    def fail():
        raise TimeoutError("probe took too long")
    monkeypatch.setattr(service_health,"snapshot",fail)
    text,metadata=system_health.collect_report()
    assert "לא ניתן להסיק" in text
    assert metadata["probe_outcome"]=="failed"
    assert metadata["error_type"]=="TimeoutError"


def test_same_backend_as_native_health(monkeypatch):
    from hub import service_health
    stamp=time.time()
    calls=[]
    def check():
        calls.append(True)
        return {"checked_at":stamp,"services":[],"network":{},"connectors":{},"overall_status":"operational"}
    monkeypatch.setattr(service_health,"snapshot",check)
    text,metadata=system_health.collect_report()
    assert calls==[True]
    assert metadata["checked_at"]==stamp
    assert "תקין" in text
