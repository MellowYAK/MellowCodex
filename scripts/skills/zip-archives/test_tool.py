import pathlib,tempfile,subprocess,sys,json
def run(a):
 p=subprocess.run([sys.executable,'tool.py'],input=json.dumps(a),capture_output=True,text=True)
 assert p.returncode==0,(p.stdout,p.stderr)
 return json.loads(p.stdout)
import zipfile
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);s=p/'source';s.mkdir();(s/'a.txt').write_text('sample')
 run({'operation':'create','source':str(s),'destination':str(p/'a.zip')})
 run({'operation':'extract','source':str(p/'a.zip'),'destination':str(p/'out')})
 assert (p/'out/a.txt').read_text()=='sample'
 with zipfile.ZipFile(p/'bad.zip','w') as z: z.writestr('../escape.txt','bad')
 q=subprocess.run([sys.executable,'tool.py'],input=json.dumps({'operation':'extract','source':str(p/'bad.zip'),'destination':str(p/'unsafe')}),capture_output=True,text=True)
 assert q.returncode!=0 and not (p/'escape.txt').exists()
print('ZIP roundtrip and traversal rejection passed')
