from hub import health_diagnostics as d
from hub import service_health as h

def test_ssh_auth_and_forwarding_are_distinct():
 assert d.classify_ssh(1,'Authenticated to relay using publickey. Remote command denied')['status']=='operational'
 assert d.classify_ssh(255,'Permission denied (publickey).')['code']=='ssh_authentication_failed'
 assert d.classify_ssh(255,'Host key verification failed.')['code']=='ssh_host_key_verification_failed'
 assert d.classify_ssh(255,'Connection timed out')['code']=='ssh_network_unreachable'

def test_safe_failure_reason_never_returns_raw_stderr(tmp_path,monkeypatch):
 monkeypatch.setattr(h,'JOBS',tmp_path)
 (tmp_path/'fixture.controller.log').write_text('private-token-do-not-output\nPort ownership unverified for guard_gateway')
 result=d.controller_failure(h,'fixture',1)
 assert result['code']=='ownership_unverified'
 assert 'private-token' not in str(result)

def test_ssh_evidence_expires_without_claiming_disconnection(tmp_path,monkeypatch):
 monkeypatch.setattr(h,'STATE',tmp_path)
 h.write(tmp_path/'ssh-health-evidence.json',dict(status='operational',checked_at=0))
 assert d.ssh_evidence(h)['status']=='stale'
