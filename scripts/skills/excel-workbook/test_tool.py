import pathlib,tempfile,subprocess,sys,json
def run(a):
 p=subprocess.run([sys.executable,'tool.py'],input=json.dumps(a),capture_output=True,text=True)
 assert p.returncode==0,(p.stdout,p.stderr)
 return json.loads(p.stdout)
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);a=str(p/'a.xlsx');b=str(p/'b.xlsx')
 run({'operation':'create','destination':a,'rows':[['Name','Value'],['sample',3]]})
 run({'operation':'edit','source':a,'destination':b,'cells':{'B2':7}})
 assert run({'operation':'read','source':b})['rows'][1][1]==7
 assert run({'operation':'read','source':a})['rows'][1][1]==3
print('XLSX create/read/edit round trip passed')
