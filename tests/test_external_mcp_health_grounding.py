"""Live authenticated MCP proof must not be masked by an inconclusive local probe."""
import time
from hub import health_diagnostics as d, service_health as h

def test_external_proof_overrides_only_inconclusive_live_path(tmp_path,monkeypatch):
    monkeypatch.setattr(h,'STATE',tmp_path)
    now=time.time()
    d.observe(h,'mellowcodex','success',now)
    d.observe(h,'guard','success',now)
    data={'checked_at':now,'network':{'state':'available'},
          'services':[{'id':'hub','status':'unverified','port_open':True,'dimensions':{}},
                      {'id':'gateway','status':'unverified','port_open':True,'dimensions':{}},
                      {'id':'guard_gateway','status':'unverified','port_open':True,'dimensions':{}},
                      {'id':'relay','status':'operational','dimensions':{}}]}
    out=d.refresh_connector_evidence(h,data,now)
    assert [s['status'] for s in out['services'][:3]]==['operational']*3
    assert out['local_overall_status']=='operational'
    assert all(s['health_basis']=='verified_external_mcp_path' for s in out['services'][:3])
    assert out['services'][3]['tunnel_verified']

def test_external_proof_does_not_hide_confirmed_service_failures(tmp_path,monkeypatch):
    monkeypatch.setattr(h,'STATE',tmp_path)
    now=time.time()
    d.observe(h,'mellowcodex','success',now)
    rows=[{'id':'hub','status':'failed','port_open':True,'dimensions':{}},
          {'id':'gateway','status':'unverified','port_open':False,'dimensions':{}},
          {'id':'guard_gateway','status':'intentionally_stopped','port_open':True,'dimensions':{}}]
    out=d.refresh_connector_evidence(h,{'checked_at':now,'network':{'state':'available'},'services':rows},now)
    assert [s['status'] for s in out['services']]==['failed','unverified','intentionally_stopped']
    assert out['local_overall_status']=='failed'

def test_expired_proof_cannot_promote_unverified(tmp_path,monkeypatch):
    monkeypatch.setattr(h,'STATE',tmp_path)
    now=time.time()
    d.observe(h,'mellowcodex','success',now)
    row={'id':'hub','status':'unverified','port_open':True,'dimensions':{}}
    out=d.refresh_connector_evidence(h,{'checked_at':now+150,'network':{'state':'available'},'services':[row]},now+150)
    assert out['services'][0]['status']=='unverified'
