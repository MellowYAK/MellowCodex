import json,subprocess,sys
p=subprocess.run([sys.executable,'tool.py'],input='{"limit":5}',text=True,capture_output=True,timeout=25)
assert p.returncode==0,p.stderr+p.stdout
r=json.loads(p.stdout);assert isinstance(r['windows'],list)
p=subprocess.run([sys.executable,'tool.py'],input='{"limit":0}',text=True,capture_output=True,timeout=10)
assert p.returncode!=0
print('window enumeration and invalid-limit rejection passed')
