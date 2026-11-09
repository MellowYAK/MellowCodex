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
import subprocess
from pywinauto import Desktop
def main(a):
 op=a['operation']
 if op=='launch':
  exe=absolute(a['executable'])
  if not exe.is_file() or exe.suffix.lower()!='.exe': raise ValueError('Existing EXE required')
  args=a.get('args',[])
  if not isinstance(args,list) or not all(isinstance(x,str) for x in args): raise ValueError('args must be string array')
  p=subprocess.Popen([str(exe),*args],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,shell=False)
  return {'pid':p.pid,'executable':str(exe)}
 h=a['handle']
 if type(h)!=int or h<=0: raise ValueError('positive handle required')
 w=Desktop(backend='win32').window(handle=h).wrapper_object()
 if op=='inspect': return {'handle':h,'title':w.window_text(),'class':w.class_name(),'children':[{'handle':int(c.handle),'title':c.window_text(),'class':c.class_name()} for c in w.children()]}
 if op=='fill': w.set_edit_text(a['text']);return {'text':w.window_text()}
 if op=='click': w.click();return {'clicked':h}
 raise ValueError('operation launch|inspect|fill|click')

if __name__=='__main__':
 try: print(json.dumps(main(json.load(sys.stdin)),ensure_ascii=False,default=str))
 except Exception as e: print(json.dumps({'error':str(e)}));sys.exit(1)
