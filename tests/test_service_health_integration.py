from hub import service_health as h

def test_native_hook_and_legacy_shutdown_share_manager():
 from pathlib import Path
 root=Path(h.__file__).parent
 assert 'health_panel=install_service_health(window,owner_toolbar,menu,open_owner_control)' in (root/'desktop_app.py').read_text(encoding='utf8')
 source=(root/'app.py').read_text(encoding='utf8')
 assert "submit,'Stop','all',body.get('request_id',''),True" in source
