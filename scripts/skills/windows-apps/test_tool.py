import pathlib,tempfile,subprocess,sys,json
def run(a):
 p=subprocess.run([sys.executable,'tool.py'],input=json.dumps(a),capture_output=True,text=True)
 assert p.returncode==0,(p.stdout,p.stderr)
 return json.loads(p.stdout)
import time,psutil
fixture="import ctypes as c,sys,json\nfrom ctypes import wintypes as w\nu=c.windll.user32;k=c.windll.kernel32\nCB=c.WINFUNCTYPE(c.c_ssize_t,w.HWND,w.UINT,w.WPARAM,w.LPARAM)\nu.DefWindowProcW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];u.DefWindowProcW.restype=c.c_ssize_t\n@CB\ndef proc(h,m,wp,lp):\n if m==273: u.SetWindowTextW(h,'Clicked');return 0\n return u.DefWindowProcW(h,m,wp,lp)\nclass WC(c.Structure):\n _fields_=[('style',w.UINT),('proc',CB),('cbClsExtra',c.c_int),('cbWndExtra',c.c_int),('instance',w.HINSTANCE),('icon',w.HICON),('cursor',w.HANDLE),('background',w.HBRUSH),('menu',w.LPCWSTR),('name',w.LPCWSTR)]\nk.GetModuleHandleW.restype=w.HMODULE\ninst=k.GetModuleHandleW(None);wc=WC();wc.proc=proc;wc.instance=inst;wc.name='MellowSkillFixture'\nu.RegisterClassW(c.byref(wc))\nu.CreateWindowExW.argtypes=[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,c.c_int,c.c_int,c.c_int,c.c_int,w.HWND,w.HMENU,w.HINSTANCE,w.LPVOID];u.CreateWindowExW.restype=w.HWND\nroot=u.CreateWindowExW(0,wc.name,'Fixture',0x10CF0000,0,0,320,150,None,None,inst,None)\nedit=u.CreateWindowExW(0,'Edit','',0x50000000,10,10,200,25,root,None,inst,None)\nbutton=u.CreateWindowExW(0,'Button','Test',0x50000000,10,45,100,25,root,None,inst,None)\nassert root and edit and button\nopen(sys.argv[1],'w').write(json.dumps({'root':root,'edit':edit,'button':button}))\nmsg=w.MSG()\nwhile u.GetMessageW(c.byref(msg),None,0,0)>0:\n u.TranslateMessage(c.byref(msg));u.DispatchMessageW(c.byref(msg))\n"
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);script=p/'ui.py';script.write_text(fixture);state=p/'state.json'
 r=run({'operation':'launch','executable':sys.executable,'args':[str(script),str(state)]})
 proc=psutil.Process(r['pid'])
 try:
  for _ in range(40):
   if state.exists(): break
   time.sleep(.1)
  assert state.exists(),'UI fixture did not start'
  h=json.loads(state.read_text())
  assert run({'operation':'fill','handle':h['edit'],'text':'sample'})['text']=='sample'
  run({'operation':'click','handle':h['button']})
  assert run({'operation':'inspect','handle':h['root']})['title']=='Clicked'
 finally:
  if proc.is_running(): proc.terminate();proc.wait(5)
print('Application launch, control fill/click/inspect passed')
