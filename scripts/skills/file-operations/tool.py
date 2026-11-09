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
import shutil
def main(a):
 op=a['operation']
 if op=='mkdir':
  p=output(a['destination']);p.mkdir();return {'created':str(p)}
 src=absolute(a['source']);dst=output(a['destination'])
 if not src.exists(): raise FileNotFoundError(str(src))
 if src.is_dir() and dst.is_relative_to(src): raise ValueError('Destination inside source')
 if op=='copy':
  if src.is_dir(): shutil.copytree(src,dst)
  else: shutil.copy2(src,dst)
 elif op=='move': shutil.move(str(src),str(dst))
 else: raise ValueError('operation: copy,move,mkdir')
 return {'destination':str(dst),'exists':dst.exists()}

if __name__=='__main__':
 try: print(json.dumps(main(json.load(sys.stdin)),ensure_ascii=False,default=str))
 except Exception as e: print(json.dumps({'error':str(e)}));sys.exit(1)
