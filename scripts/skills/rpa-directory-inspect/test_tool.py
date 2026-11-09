import tempfile,pathlib,subprocess,json,sys
with tempfile.TemporaryDirectory() as d:
 pathlib.Path(d,'sample.txt').write_text('abc')
 p=subprocess.run([sys.executable,'tool.py'],input=json.dumps({'path':d}),text=True,encoding='utf-8',capture_output=True,timeout=30)
 assert p.returncode==0,p.stderr+p.stdout
 r=json.loads(p.stdout);assert any(f['name']=='sample.txt' and f['size']==3 for f in r['files']),r
print('RPA FileSystem real file metadata passed')
