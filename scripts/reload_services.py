import sqlite3,psutil
from pathlib import Path
c=sqlite3.connect(r'E:\AI\state\hub.sqlite3')
assert not c.execute("select id from tasks where state in ('running','queued','verifying')").fetchall(),'Active tasks; restart refused'
v=[]
for p in psutil.process_iter(['name','cmdline']):
    if (p.info['name'] or '').lower()=='python.exe' and any(x in ' '.join(p.info['cmdline'] or []) for x in ['hub.app:app','hub.mcp_gateway']):v.append(p)
for p in v:
    try:p.terminate()
    except psutil.NoSuchProcess:pass
psutil.wait_procs(v,timeout=8)
