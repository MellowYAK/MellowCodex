"""Regression: preserve Guard source-of-truth evidence in compact health UI."""
from hub.service_health import compact_status

def test_guard_supervisor_fields_visible_without_inventing_ownership():
    data = dict(schema_version=1, checked_at=123.0, overall_status='operational',
      local_overall_status='operational',external_connectors_status='operational',
      connectors={},network={},guard_supervisor={'healthy': True,'supervisor_healthy':False},
      active_tasks=[],reset_scope=None,
      services=[dict(id='guard',name='Mellow Guard',status='operational',reason='Verified existing pair',
                     checked_at=123.0,mcp_api_verified=True,supervisor_healthy=False,
                     observed_healthy=True,health_basis='verified_existing_services')])
    row=compact_status(data)['services'][0]
    assert row['mcp_api_verified'] is True
    assert row['supervisor_healthy'] is False
    assert row['observed_healthy'] is True
    assert row['health_basis']=='verified_existing_services'
    data['services'][0].update(supervisor_healthy=True,health_basis='supervisor_started')
    row=compact_status(data)['services'][0]
    assert row['supervisor_healthy'] is True
    assert row['health_basis']=='supervisor_started'
