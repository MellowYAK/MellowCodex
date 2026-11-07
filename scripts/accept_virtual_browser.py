"""Real Engine/Qt browser acceptance against an isolated synthetic input page."""
import asyncio,json,os,sys,time,threading,subprocess
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
sys.stdout.reconfigure(encoding='utf-8')
PAGE=b'''<!doctype html><html><body style="font:24px Arial;background:white;color:black"><h1>Virtual pointer acceptance</h1><button id="click" style="position:absolute;left:40px;top:100px;width:180px;height:65px" onclick="record('clicked')">Click me</button><div id="drag" style="position:absolute;left:40px;top:250px;width:120px;height:80px;background:#268bd2;color:white">Drag from here</div><div style="position:absolute;left:340px;top:250px;width:160px;height:80px;background:#e0efbe">Drop here</div><p id="status" style="position:absolute;top:390px">Waiting for actions</p><script>let pressed=false;function record(action){document.getElementById('status').textContent+=' '+action;fetch('/event',{method:'POST',body:JSON.stringify({action})})}document.getElementById('drag').onmousedown=()=>pressed=true;document.onmouseup=e=>{if(pressed&&e.clientX>=340&&e.clientX<=500&&e.clientY>=250&&e.clientY<=330)record('dragged');pressed=false}</script></body></html>'''
EVENTS=[]
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(PAGE)
 def do_POST(self):
  EVENTS.append(json.loads(self.rfile.read(min(1000,int(self.headers.get('Content-Length','0'))))))
  self.send_response(204);self.end_headers()
 def log_message(self,*args):pass

async def main():
 from hub.config import ROOT,STATE,PORT,CDP_PORT,OLLAMA
 if ROOT.resolve()==Path('E:/AI').resolve() or CDP_PORT==9223 or PORT==8876:raise RuntimeError('Use isolated root/API/CDP ports')
 from hub.store import Store
 from hub.conversations import Conversations
 from hub.engine import Engine
 from hub.model_settings import ModelSettings,save_settings
 async with httpx.AsyncClient(timeout=10,trust_env=False) as client:
  if (await client.get(OLLAMA+'/api/ps')).json().get('models'):raise RuntimeError('Ollama busy')
 save_settings(ModelSettings(model='qwen3.5:4b',visual_guidance=False,keep_alive_minutes=2,request_timeout_seconds=300))
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
 log=(ROOT/'runtime.log').open('w',encoding='utf-8')
 children=[];engine=None
 try:
  for args in [['-m','uvicorn','hub.app:app','--host','127.0.0.1','--port',str(PORT)],['-m','hub.desktop_app','--background']]:
   children.append(subprocess.Popen([sys.executable,*args],cwd=Path(__file__).resolve().parents[1],stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW))
  for _ in range(80):
   if (STATE/'browser-endpoint.json').exists():break
   if any(p.poll() is not None for p in children):raise RuntimeError('Owned runtime exited; inspect runtime.log')
   await asyncio.sleep(.25)
  else:raise RuntimeError('Owned browser not ready')
  async with httpx.AsyncClient(timeout=3,trust_env=False) as ready_client:
   for _ in range(80):
    try:
     ready=await ready_client.get(f'http://127.0.0.1:{PORT}/')
     if ready.status_code==200:break
    except httpx.HTTPError:pass
    await asyncio.sleep(.25)
   else:raise RuntimeError('Owned API not ready')
  root=ROOT/'fixture';root.mkdir(exist_ok=True)
  store=Store(STATE/'hub.sqlite3');conversations=Conversations(store);project=conversations.project(str(root));chat=conversations.create(project['id'])
  task=conversations.submit(chat['id'],f'Open http://127.0.0.1:{server.server_port}/ in the embedded browser. Use browser_frame to inspect the page, then browser_pointer click the Click me button and browser_pointer drag the blue Drag from here box into the green Drop here box. Get a fresh browser_frame before each input. Prefer the observed ref/end_ref fields from controls/text_regions rather than estimating coordinates. Verify the page status contains clicked and dragged. Use only the virtual pointer for these two actions; do not use browser_script, DOM clicks, shell, native input or physical mouse. Report observed results.','browser','virtual-pointer-'+str(time.time_ns()))
  engine=Engine(store);started=time.monotonic();await asyncio.wait_for(engine.run(task['id']),720)
  actions=store.actions(task['id']);final=store.get(task['id'])
  evidence={'task_id':task['id'],'elapsed_seconds':round(time.monotonic()-started,2),'state':final['state'],'result':final['result'],'actions':actions,'page_events':EVENTS,'verified':{'clicked','dragged'}<={e.get('action') for e in EVENTS} and any(a['tool']=='browser_pointer' for a in actions)}
  (ROOT/'acceptance.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in evidence.items() if k!='actions'},ensure_ascii=False))
 finally:
  if engine:await engine.runner.browser.disconnect()
  for process in reversed(children):
   if process.poll() is None:
    import psutil
    try:
     owner=psutil.Process(process.pid)
     for child in owner.children(recursive=True):
      try:child.terminate()
      except psutil.Error:pass
     process.terminate();process.wait(10)
    except (psutil.Error,subprocess.TimeoutExpired):pass
  server.shutdown();log.close()
  async with httpx.AsyncClient(timeout=60,trust_env=False) as client:
   await client.post(OLLAMA+'/api/generate',json={'model':'qwen3.5:4b','keep_alive':0})
   print(json.dumps({'remaining_models':(await client.get(OLLAMA+'/api/ps')).json().get('models',[])}))

if __name__=='__main__':asyncio.run(main())
