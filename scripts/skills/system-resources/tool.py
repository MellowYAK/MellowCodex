import json,sys,pathlib,os
def absolute(value):
 p=pathlib.Path(value)
 if not p.is_absolute(): raise ValueError('Absolute path required')
 return p.resolve()
def output(value):
 p=absolute(value)
 if p.exists(): raise FileExistsError(str(p))
 if not p.parent.is_dir(): raise ValueError('Parent directory must exist')
 return p
import psutil
def main(a):
 limit=a.get('limit',30)
 if type(limit)!=int or not 1<=limit<=200: raise ValueError('limit1..200')
 rows=[]
 for p in psutil.process_iter(['pid','name','memory_info']):
  try:
   i=p.info;rows.append({'pid':i['pid'],'name':i['name'],'rss':i['memory_info'].rss})
  except (psutil.NoSuchProcess,psutil.AccessDenied): pass
 rows.sort(key=lambda x:x['rss'],reverse=True)
 return {'cpu_percent':psutil.cpu_percent(interval=.2),'memory':psutil.virtual_memory()._asdict(),'processes':rows[:limit]}

if __name__=='__main__':
 try: print(json.dumps(main(json.load(sys.stdin)),ensure_ascii=False,default=str))
 except Exception as e: print(json.dumps({'error':str(e)}));sys.exit(1)
