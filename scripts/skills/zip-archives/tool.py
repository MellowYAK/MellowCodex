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
import zipfile,stat
def main(a):
 op=a['operation'];src=absolute(a['source']);dst=output(a['destination'])
 if op=='create':
  entries=list(src.rglob('*')) if src.is_dir() else [src]
  if src.is_dir() and dst.is_relative_to(src): raise ValueError('ZIP must be outside source')
  with zipfile.ZipFile(dst,'x',zipfile.ZIP_DEFLATED) as z:
   for p in entries:
    if p.is_symlink(): raise ValueError('Symlinks not supported')
    if p.is_file(): z.write(p,p.relative_to(src) if src.is_dir() else p.name)
  return {'saved':str(dst)}
 if op!='extract': raise ValueError('operation create|extract')
 with zipfile.ZipFile(src) as z:
  members=z.infolist()
  if sum(m.file_size for m in members)>2*1024**3: raise ValueError('Uncompressed archive exceeds2GiB')
  for m in members:
   name=m.filename.replace('\\','/')
   target=(dst/name).resolve()
   if ':' in name or not target.is_relative_to(dst) or stat.S_ISLNK(m.external_attr>>16): raise ValueError('Unsafe ZIP member')
  dst.mkdir()
  z.extractall(dst)
 return {'extracted':str(dst),'entries':len(members)}

if __name__=='__main__':
 try: print(json.dumps(main(json.load(sys.stdin)),ensure_ascii=False,default=str))
 except Exception as e: print(json.dumps({'error':str(e)}));sys.exit(1)
