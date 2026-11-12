from types import SimpleNamespace
from hub import service_health as h

def test_relay_status_explicitly_imports_filehash_before_guard_common(monkeypatch,tmp_path):
    guard=tmp_path/'guard'
    (guard/'releases'/'v1').mkdir(parents=True)
    monkeypatch.setattr(h,'GUARD',guard)
    seen=[]
    def fake_ps(script,timeout):
        seen.append(script)
        return SimpleNamespace(stdout='{"state":"running","owned":true}',stderr='',returncode=0)
    monkeypatch.setattr(h,'ps',fake_ps)
    result=h.relay_status({'release_id':'v1'})
    assert result['state']=='available'
    assert result['process_verified'] is True
    cmd=seen[0]
    assert cmd.index('Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop') < cmd.index('common.ps1')
    assert 'Set-GuardRelayEnvironment' in cmd

def test_invalid_or_empty_relay_output_remains_unverified(monkeypatch,tmp_path):
    guard=tmp_path/'guard'
    (guard/'releases'/'v1').mkdir(parents=True)
    monkeypatch.setattr(h,'GUARD',guard)
    monkeypatch.setattr(h,'ps',lambda script,timeout:SimpleNamespace(stdout='',stderr='failure',returncode=1))
    result=h.relay_status({'release_id':'v1'})
    assert result['state']=='unknown'
    assert result['diagnostic_code']=='JSONDecodeError'
