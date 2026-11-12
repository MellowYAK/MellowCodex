"""Only a fresh authenticated remote Guard proof can close local 401 ambiguity."""
import time
import pytest
from hub import service_health as h
from hub import health_diagnostics as d

@pytest.mark.parametrize("owned,port_open,http,proof,expected", [
 (True,True,401,True,'operational'),
 (True,True,401,False,'unverified'),
 (False,True,401,True,'unverified'),
 (True,False,401,True,'unverified'),
 (True,True,503,True,'unverified'),
 (True,True,200,True,'unverified')
])
def test_guard_correlates_real_external_proof_with_live_owned_endpoint(tmp_path,monkeypatch,owned,port_open,http,proof,expected):
    monkeypatch.setattr(h,'STATE',tmp_path)
    now=time.time()
    if proof:
        d.observe(h,'guard','success',now)
    row=dict(id='guard',status='unverified',state='unknown',owned=owned,port_open=port_open,
             http_status=http,dimensions={})
    result=d.refresh_connector_evidence(h,dict(network={'state':'available'},services=[row]),now)
    assert result['services'][0]['status']==expected
    assert result['local_overall_status']==expected
    if expected!='operational':
        assert result['overall_status']!='operational'

def test_guard_verified_proof_expiry_does_not_leave_false_green(tmp_path,monkeypatch):
    monkeypatch.setattr(h,'STATE',tmp_path)
    now=time.time();d.observe(h,'guard','success',now)
    row=dict(id='guard',status='unverified',owned=True,port_open=True,http_status=401,dimensions={})
    current=d.refresh_connector_evidence(h,dict(network={'state':'available'},services=[row.copy()]),now)
    assert current['local_overall_status']=='operational'
    expired=d.refresh_connector_evidence(h,dict(network={'state':'available'},services=[row.copy()]),now+121)
    assert expired['local_overall_status']=='unverified'
    assert expired['connectors']['guard']['status']=='stale'
