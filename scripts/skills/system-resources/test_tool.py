import pathlib,tempfile,subprocess,sys,json
def run(a):
 p=subprocess.run([sys.executable,'tool.py'],input=json.dumps(a),capture_output=True,text=True)
 assert p.returncode==0,(p.stdout,p.stderr)
 return json.loads(p.stdout)
r=run({'limit':5});assert r['memory']['total']>0 and 0<=r['cpu_percent']<=100 and len(r['processes'])>0
print('Actual CPU/RAM/process observation passed')
