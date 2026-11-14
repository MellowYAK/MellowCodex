"""Deterministic, source-backed system health reports for every local chat.

Use the existing service_health.snapshot shared by desktop and MCP. This module
does not infer health from chat history or invoke a local language model.
"""
import re
import time
import unicodedata
from datetime import datetime

_ALIASES = {
    "status", "system status", "service status", "services status",
    "status check", "check status", "check system status",
    "system health", "health check", "check health",
    "check all services", "check services", "are services running",
    "status of services", "status of the system",
    "סטטוס", "בדוק סטטוס", "בדיקת סטטוס", "מצב המערכת", "מצב מערכת",
    "מצב שירותים", "סטטוס שירותים", "סטטוס המערכת", "בדיקת בריאות",
    "בדיקת בריאות המערכת", "בדוק בריאות", "בדוק שירותים",
    "בדוק את כל השירותים", "מה מצב השירותים", "האם הכל תקין",
    "статус", "проверь статус", "статус системы", "состояние системы",
    "проверка здоровья", "проверка сервисов", "проверь сервисы",
    "проверить статус", "проверь все сервисы", "состояние сервисов",
    "estado", "estado del sistema", "verificar estado", "état",
    "état du système", "statut", "zustand", "systemstatus",
    "status prüfen", "stato", "stato del sistema", "durum",
    "sistem durumu", "系统状态", "状态", "状態", "システム状態", "상태", "시스템 상태",
}
_STATES = {
    "operational": "תקין", "available": "זמין", "degraded": "מוגבל",
    "failed": "נכשל", "unverified": "אימות לא הושלם",
    "stale": "ראיה ישנה", "starting": "מופעל", "intentionally_stopped": "הופסק בכוונה",
    "reauthentication_required": "נדרש חיבור מחדש",
    "idle": "לא טעון (לא בהכרח תקלה)", "unknown": "בדיקה ללא תוצאה",
    "error": "כשל בדיקה", "stopped": "כבוי", "warning": "אזהרה",
}
def _normalize(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    value = re.sub(r"[\u200c-\u200f\u202a-\u202e]", "", value)
    return re.sub(r"[^\w]+", " ", value, flags=re.UNICODE).strip()

_NORMALIZED = frozenset(_normalize(p) for p in _ALIASES)

def is_status_request(value):
    """Only an isolated system-health intent, never arbitrary task-status prose."""
    phrase = _normalize(value)
    return bool(phrase) and phrase in _NORMALIZED

def _time(stamp):
    if not isinstance(stamp, (int, float)) or stamp <= 0:
        return "אין חותמת זמן"
    return datetime.fromtimestamp(stamp).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")

def _age(stamp, reference):
    if not isinstance(stamp, (int, float)) or stamp <= 0:
        return "לא קיימת ראיה קודמת"
    return str(max(0, round(reference-stamp))) + " שניות"

def format_report(snapshot):
    checked = snapshot.get("checked_at") or time.time()
    lines = [
        "בדיקת בריאות מלאה של MellowCodex",
        "זמן בדיקה: " + _time(checked),
        "מצב השירותים המקומיים: " + _STATES.get(
            snapshot.get("local_overall_status", snapshot.get("overall_status")),
            str(snapshot.get("overall_status", "לא ידוע"))),
        "",
        "שירותים שנבדקו:",
    ]
    for s in snapshot.get("services", []):
        state = s.get("status", s.get("state", "unknown"))
        lines.append("- " + str(s.get("name") or s.get("id")) + ": " +
                     _STATES.get(state, str(state)) +
                     " | " + str(s.get("reason") or "אין פירוט מהבדיקה") +
                     " | נבדק: " + _time(s.get("checked_at")) +
                     " | גיל ראיה: " + _age(s.get("checked_at"), checked))
    network = snapshot.get("network") or {}
    lines.append("")
    lines.append("רשת: " + str(network.get("state", "unknown")) +
                 " | " + str(network.get("reason", "לא התקבלה תוצאת אבחון")))
    guard = snapshot.get("guard_supervisor") or {}
    lines.append("פיקוח Guard על Hub:")
    if guard.get("state") == "verified":
        lines.append("- שירות Hub: " + ("תקין" if guard.get("healthy") is True else
                     "לא אומת" if guard.get("healthy") is None else "דורש בדיקה"))
        lines.append("- הפעלה בבעלות Guard: " + (
            "אומתה" if guard.get("supervisor_healthy") is True else
            "לא אומתה; השירות עשוי לפעול תחת תהליך אחר"))
        lines.append("- תקינות תהליכים נצפית: " + (
            "אומתה" if guard.get("observed_healthy") is True else "לא אומתה"))
        lines.append("- בסיס ראיה: " + str(guard.get("health_basis") or "unknown"))
    else:
        lines.append("- בדיקת Guard עצמאית: לא אומתה | " +
                     str(guard.get("reason") or "לא התקבלה ראיה מאומתת"))
    coverage = snapshot.get("diagnostic_coverage") or {}
    if coverage:
        lines.append("כיסוי אבחון: " + _STATES.get(
            coverage.get("status"),str(coverage.get("status","unknown"))) +
            " | " + str(coverage.get("reason") or "אין פירוט"))
    lines.append("חיבורי MCP חיצוניים:")
    for key,c in (snapshot.get("connectors") or {}).items():
        lines.append("- " + key + ": " + _STATES.get(c.get("status"),str(c.get("status"))) +
                     " | " + str(c.get("reason","")) +
                     " | בדיקה אחרונה: " + _time(c.get("checked_at")) +
                     " | הצלחה אחרונה: " + _time(c.get("last_success_at")))
    lines.append("ראיות MCP מאשרות את מסלול החיבור שנבדק, לא בהכרח בדיקת SSH עצמאית.")
    lines.append("כשל של כלי אבחון אינו הוכחה שהשירות עצמו נפל. מודל שאינו טעון אינו תקלה כשפריקתו מכוונת.")
    return "\n".join(lines)

def collect_report():
    """Bounded, read-only self-recovery for transient status probes."""
    from . import service_health
    errors = []
    data = None
    for attempt in range(2):
        try:
            data = service_health.snapshot()
            break
        except Exception as exc:
            errors.append(type(exc).__name__)
            retryable = isinstance(exc, (TimeoutError, ConnectionError)) or type(exc).__name__ in (
                "ReadTimeout", "ConnectTimeout", "ConnectError", "TimeoutException")
            if attempt == 0 and retryable:
                time.sleep(0.1)
                continue
            break
    if data is None:
        previous = service_health.read(service_health.STATE / "health-snapshot.json")
        last = previous.get("checked_at")
        prior_text = (("\nדוח קודם מ־" + _time(last) +
                       " קיים, אך הוא לא אומת כעת.") if isinstance(last,(int,float)) and last>0 else "")
        message = ("בדיקת הבריאות החיה לא הושלמה (" +
                   (errors[-1] if errors else "UnknownError") +
                   "). לא ניתן להסיק מכך שהשירותים נפלו." + prior_text)
        return message, {
            "probe_outcome":"failed","error_type":(errors[-1] if errors else "UnknownError"),"checked_at":time.time(),
            "previous_snapshot_at":last,
            "service_statuses":{r.get("id"):"stale" for r in previous.get("services",[])
                                if isinstance(r,dict) and r.get("id")},
            "diagnostic_recovery":{"strategy":"bounded_read_only_retry",
                                   "attempts":len(errors),"recovered":False,
                                   "error_types":errors,"restart_performed":False}}
    message = format_report(data)
    if errors:
        message += "\nבדיקת האבחון הצליחה בניסיון חוזר, ללא אתחול שירותים."
    return message, {
        "probe_outcome":"completed","checked_at":data.get("checked_at"),
        "service_statuses":{r.get("id"):r.get("status") for r in data.get("services",[])},
        "connector_statuses":{k:v.get("status") for k,v in data.get("connectors",{}).items()},
        "snapshot_schema":data.get("schema_version"),
        "diagnostic_recovery":{"strategy":"bounded_read_only_retry",
                               "attempts":len(errors)+1,"recovered":bool(errors),
                               "error_types":errors,"restart_performed":False}}
