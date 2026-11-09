import pathlib,tempfile,subprocess,sys,json
def run(a):
 p=subprocess.run([sys.executable,'tool.py'],input=json.dumps(a),capture_output=True,text=True)
 assert p.returncode==0,(p.stdout,p.stderr)
 return json.loads(p.stdout)
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);s=p/'src';s.mkdir();(s/'sample.txt').write_text('sample');dst=p/'dst'
 run({'operation':'copy','source':str(s),'destination':str(dst),'dry_run':False})
 assert (dst/'sample.txt').read_text()=='sample'
 (dst/'extra.txt').write_text('extra')
 run({'operation':'sync','source':str(s),'destination':str(dst)})
 assert (dst/'extra.txt').exists()
 assert 'sample.txt' in run({'operation':'list','source':str(dst)})['stdout']
print('rclone real local copy/list and non-destructive sync preview passed')
