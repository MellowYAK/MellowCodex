"""Public health probe failures stay distinct from verified live MCP operations."""

def test_live_mcp_does_not_turn_public_503_into_whole_system_failure(tmp_path,monkeypatch):
    import time
    from hub import health_diagnostics as d, service_health as h
    monkeypatch.setattr(h,"STATE",tmp_path)
    now=time.time()
    d.observe(h,"mellowcodex","success",now)
    data={"checked_at":now,"network":{"state":"error","forwarding":"failed",
          "forwarded_http_status":503},
          "services":[{"id":"hub","status":"operational","dimensions":{}}]}
    result=d.refresh_connector_evidence(h,data,now)
    assert result["overall_status"]=="operational"
    assert result["network"]["state"]=="error"
    assert result["diagnostic_coverage"]["status"]=="degraded"
    assert result["diagnostic_coverage"]["independent_public_health_failure"] is True

def test_public_503_with_no_live_mcp_stays_degraded(tmp_path,monkeypatch):
    import time
    from hub import health_diagnostics as d, service_health as h
    monkeypatch.setattr(h,"STATE",tmp_path)
    now=time.time()
    data={"checked_at":now,"network":{"state":"error","forwarding":"failed",
          "forwarded_http_status":503},
          "services":[{"id":"hub","status":"operational","dimensions":{}}]}
    result=d.refresh_connector_evidence(h,data,now)
    assert result["overall_status"]=="degraded"
    assert result["diagnostic_coverage"]["independent_public_health_failure"] is False
