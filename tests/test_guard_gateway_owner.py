import json
from hub.guardian.control_plane import Services

def test_relay_owns_gateway_only_when_enabled(tmp_path):
    state=tmp_path/'state';state.mkdir()
    service=Services({'root':str(tmp_path)})
    assert not service.gateway_managed_by_hub()
    (state/'relay.json').write_text(json.dumps({'enabled':False}))
    assert not service.gateway_managed_by_hub()
    (state/'relay.json').write_text(json.dumps({'enabled':True}))
    assert service.gateway_managed_by_hub()
