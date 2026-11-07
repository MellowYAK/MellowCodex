import time
from hub.terminal_sessions import Terminals

def test_live_command(tmp_path):
    t=Terminals();task={'id':'test','workspace':str(tmp_path)}
    r=t.start(task,tmp_path,"Write-Output 'before'; Start-Sleep -Seconds 1; Write-Output 'after'",'powershell')
    assert r['state']=='running'
    for _ in range(30):
        r=t.read(task,r['session_id'])
        if r['state']=='exited':break
        time.sleep(.1)
    assert r['exit_code']==0
    assert 'before' in r['output'] and 'after' in r['output']
