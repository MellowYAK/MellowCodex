import json
from unittest.mock import patch
from hub import power as p
from hub import service_health as h

def test_desktop_stop_preserves_same_boot_and_expires_next_boot(tmp_path):
    with patch.object(h,"STATE",tmp_path), patch.object(p,"settings",return_value={"start_with_windows":True}), patch.object(p,"transition_active",return_value=False), patch.object(h.psutil,"boot_time",return_value=100.0):
        p.record_stop_until_reboot()
        p.expire_stop_until_reboot()
        assert all((tmp_path/n).exists() for n in ("agent-manual-stop","mcp-manual-stop"))
        with patch.object(h.psutil,"boot_time",return_value=200.0):
            p.expire_stop_until_reboot()
        assert not any((tmp_path/n).exists() for n in ("agent-manual-stop","mcp-manual-stop"))

def test_legacy_persistent_and_disabled_startup_never_clear(tmp_path):
    with patch.object(h,"STATE",tmp_path), patch.object(p,"settings",return_value={"start_with_windows":False}), patch.object(p,"transition_active",return_value=False), patch.object(h.psutil,"boot_time",return_value=200.0):
        old=tmp_path/"agent-manual-stop"
        old.write_text("All agent services intentionally stopped")
        receipt=tmp_path/"mcp-manual-stop"
        receipt.write_text(json.dumps(dict(schema_version=1,boot_time=100.0,resume_on_next_boot=True,reason="desktop_stop")))
        p.expire_stop_until_reboot()
        assert old.exists() and receipt.exists()
        with patch.object(p,"settings",return_value={"start_with_windows":True}):
            p.expire_stop_until_reboot()
        assert old.exists() and not receipt.exists()
