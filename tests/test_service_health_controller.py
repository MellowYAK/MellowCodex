
import subprocess,sys,time
from hub import service_health as h

def test_controller_does_not_wait_for_descendant_pipe_eof(tmp_path,monkeypatch):
 monkeypatch.setattr(h,'JOBS',tmp_path)
 # Parent exits immediately; child deliberately retains inherited output.
 code="import subprocess,sys;subprocess.Popen([sys.executable,'-c','import time;time.sleep(3)'],close_fds=False)"
 before=time.monotonic()
 result=h.execute_controller([sys.executable,'-c',code],'fixture')
 assert result.returncode==0
 assert time.monotonic()-before<2.5
