import json
import os
from pathlib import Path
import subprocess
import sys


def test_worker_health_echoes_activation_identity_without_model(tmp_path):
    env=dict(os.environ,LOCAL_AGENT_ROOT=str(tmp_path/'runtime'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
    result=subprocess.run([sys.executable,'-m','hub.development.worker','--health','release-test','nonce-test'],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,encoding='utf-8',timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    assert result.returncode==0,result.stderr
    reply=json.loads(result.stdout)
    assert reply['release_id']=='release-test' and reply['nonce']=='nonce-test'
    assert reply['ready'] is True and reply['protocol']==1
