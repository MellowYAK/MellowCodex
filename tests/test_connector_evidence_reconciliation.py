"""Fresh MCP evidence changes every derived health status without fake proof."""
import time
from hub import service_health as h
from hub import health_diagnostics as d

def test_external_proof_refresh_updates_cached_service_dimensions(tmp_path,monkeypatch):
    monkeypatch.setattr(h,'STATE',tmp_path)
    monkeypatch.setattr(h,'JOBS',tmp_path/'jobs')
    now=time.time()
    snapshot=dict(checked_at=now,network={'state':'available'},services=[
        dict(id='hub',status='operational',dimensions={}),
        dict(id='gateway',status='operational',dimensions={}),
        dict(id='guard',status='operational',dimensions={}),
        dict(id='guard_gateway',status='operational',dimensions={}),
        dict(id='relay',status='operational',dimensions={})
    ])
    old=d.refresh_connector_evidence(h,snapshot,now)
    assert old['local_overall_status']=='operational'
    assert old['overall_status']=='operational'
    assert old['services'][4]['tunnel_verified'] is False
    d.observe(h,'mellowcodex','success',now)
    d.observe(h,'guard','success',now)
    refreshed=d.refresh_connector_evidence(h,snapshot,now+0.1)
    assert refreshed['overall_status']=='operational'
    assert refreshed['external_connectors_status']=='operational'
    assert refreshed['services'][1]['dimensions']['connector']['external_round_trip']=='verified'
    assert refreshed['services'][3]['dimensions']['connector']['external_round_trip']=='verified'
    assert refreshed['services'][4]['tunnel_verified'] is True
    expired=d.refresh_connector_evidence(h,snapshot,now+121)
    assert expired['local_overall_status']=='operational'
    assert expired['external_connectors_status']=='stale'
    assert expired['overall_status']=='operational'
    assert expired['services'][4]['tunnel_verified'] is False
    assert expired['services'][1]['dimensions']['connector']['status']=='stale'

def test_network_failure_is_not_covered_by_fresh_external_evidence(tmp_path,monkeypatch):
    monkeypatch.setattr(h,'STATE',tmp_path)
    now=time.time()
    d.observe(h,'mellowcodex','success',now)
    d.observe(h,'guard','success',now)
    data=dict(checked_at=now,network={'state':'error'},services=[dict(id='hub',status='operational',dimensions={})])
    result=d.refresh_connector_evidence(h,data,now)
    assert result['external_connectors_status']=='operational'
    assert result['local_overall_status']=='degraded'
    assert result['overall_status']=='degraded'

def test_failed_external_observation_does_not_turn_healthy_from_local_ports(tmp_path,monkeypatch):
    monkeypatch.setattr(h,'STATE',tmp_path)
    now=time.time()
    d.observe(h,'guard','transport_error',now)
    data=dict(checked_at=now,network={'state':'available'},services=[
        dict(id='guard_gateway',status='operational',dimensions={},port_open=True,owned=True)])
    result=d.refresh_connector_evidence(h,data,now)
    assert result['local_overall_status']=='operational'
    assert result['overall_status']=='operational'
    assert result['connectors']['guard']['external_round_trip']=='unverified'


def test_snapshot_cached_path_recomputes_overall_after_proof_and_expiry(tmp_path,monkeypatch):
    monkeypatch.setattr(h,'STATE',tmp_path)
    now=time.time()
    d.observe(h,'mellowcodex','success',now)
    d.observe(h,'guard','success',now)
    cache=dict(checked_at=now+200,network={'state':'available'},
               overall_status='stale',connectors={},
               services=[dict(id='hub',status='operational',dimensions={}),
                         dict(id='gateway',status='operational',dimensions={})])
    monkeypatch.setattr(h,'_snapshot_cache',cache)
    def must_not_run():
        raise AssertionError('No full local snapshot should run on cached path')
    monkeypatch.setattr(h,'_snapshot',must_not_run)
    monkeypatch.setattr(h.time,'time',lambda:now+1)
    fresh=h.snapshot()
    assert fresh['overall_status']=='operational'
    assert fresh['external_connectors_status']=='operational'
    assert fresh['services'][1]['dimensions']['connector']['status']=='operational'
    monkeypatch.setattr(h.time,'time',lambda:now+121)
    expired=h.snapshot()
    assert expired['overall_status']=='operational'
    assert expired['local_overall_status']=='operational'
    assert expired['services'][1]['dimensions']['connector']['status']=='stale'
