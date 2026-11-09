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
import subprocess,re
EXE='E:/AI/tools/rclone/1.76.0/rclone.exe'
def checked(p):
 if not isinstance(p,str) or not p or p.startswith('-'): raise ValueError('Path required')
 if pathlib.Path(p).is_absolute(): return str(absolute(p))
 if re.fullmatch(r'[A-Za-z0-9_-]+:.*',p): return p
 raise ValueError('Absolute local path or named remote:path required')
def main(a):
 op=a['operation']
 if op=='remotes': args=['listremotes']
 elif op=='list': args=['lsjson',checked(a['source']),'--max-depth','1']
 elif op in ('copy','sync'):
  dry=a.get('dry_run',True)
  if type(dry)!=bool: raise ValueError('dry_run boolean required')
  if op=='sync' and not dry and a.get('allow_delete') is not True: raise ValueError('Explicit allow_delete required for live sync')
  args=[op,checked(a['source']),checked(a['destination']),'--stats','0','--retries','1','--low-level-retries','1','--contimeout','10s','--timeout','30s']
  if dry: args.append('--dry-run')
 else: raise ValueError('operation remotes|list|copy|sync')
 p=subprocess.run([EXE,*args],capture_output=True,text=True,timeout=70)
 if p.returncode: raise RuntimeError(p.stderr[-4000:])
 return {'operation':op,'dry_run':a.get('dry_run',True) if op in ('copy','sync') else None,'stdout':p.stdout[:20000],'stderr':p.stderr[-4000:]}

if __name__=='__main__':
 try: print(json.dumps(main(json.load(sys.stdin)),ensure_ascii=False,default=str))
 except Exception as e: print(json.dumps({'error':str(e)}));sys.exit(1)
