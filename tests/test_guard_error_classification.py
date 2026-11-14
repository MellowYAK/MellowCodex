"""Guard transport exception groups must reveal safe classes, not secrets."""
import time
from hub import service_health as h

def test_guard_nested_errors_have_safe_diagnostic_type(monkeypatch,tmp_path):
    import asyncio
    async def fail():
        raise ExceptionGroup("secret token value",[
            TimeoutError("private credential"),
            ConnectionError("secret host")])
    def fake_run(coro):
        coro.close()
        raise ExceptionGroup("secret token value",[
            TimeoutError("private credential"),ConnectionError("secret host")])
    monkeypatch.setattr(asyncio,"run",fake_run)
    cfg={"auth_file":"ignored"}
    result=h.guard_status(cfg)
    assert result["state"]=="unknown"
    assert result["nested_error_types"]==["TimeoutError","ConnectionError"]
    assert "private credential" not in result["reason"]
    assert "secret host" not in result["reason"]
    assert "ExceptionGroup" in result["reason"]
