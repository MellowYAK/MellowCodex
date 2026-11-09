import pathlib,tempfile,subprocess,sys,json
def run(a):
 p=subprocess.run([sys.executable,'tool.py'],input=json.dumps(a),capture_output=True,text=True)
 assert p.returncode==0,(p.stdout,p.stderr)
 return json.loads(p.stdout)
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);(p/'a').write_text('sample')
 run({'operation':'copy','source':str(p/'a'),'destination':str(p/'b')})
 assert (p/'b').read_text()=='sample'
 run({'operation':'move','source':str(p/'b'),'destination':str(p/'c')})
 assert (p/'c').exists() and not (p/'b').exists()
 run({'operation':'mkdir','destination':str(p/'sub')})
 run({'operation':'copy','source':str(p/'sub'),'destination':str(p/'tree')})
 assert (p/'tree').is_dir()
print('File copy, move and directory creation passed')
