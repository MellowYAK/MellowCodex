from hub.store import Store
from hub.development.selfdevelop import SelfDevelop

def test_selfdevelop_reports_guard_scope_without_autonomy_claim(tmp_path):
    store=Store(tmp_path/'state.db')
    status=SelfDevelop(store).start('Repair own status','test:guard-status','mcp')
    assert status['supervisor']=='Mellow Guard'
    assert status['control_plane_restart_supported'] is True
    assert status['autonomous_development_verified'] is False
    assert 'desktop and dependency upgrades are not included' in status['deployment_scope']
