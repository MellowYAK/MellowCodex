import pathlib,tempfile,subprocess,sys,json
def run(a):
 p=subprocess.run([sys.executable,'tool.py'],input=json.dumps(a),capture_output=True,text=True)
 assert p.returncode==0,(p.stdout,p.stderr)
 return json.loads(p.stdout)
import threading,http.server,functools,asyncio,os
os.environ['PYTHONPATH']='E:/AI/repos/local-agent-hub'+os.pathsep+os.environ.get('PYTHONPATH','')
sys.path.insert(0,'E:/AI/repos/local-agent-hub')
from hub.browser import Browser
async def target():
 b=Browser()
 try:
  tabs=(await b.tabs())['tabs']
  return next(t['id'] for t in tabs if t['url']=='about:blank')
 finally: await b.disconnect()
tab=asyncio.run(target())
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d)
 (p/'index.html').write_text('<input id="name"><select id="choice"><option value="a">A</option><option value="b">B</option></select><button id="go" onclick="document.title=document.querySelector(\'#name\').value">Go</button><a href="/sample.txt">Download</a>')
 (p/'sample.txt').write_text('browser sample')
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*a): pass
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=d))
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 url='http://127.0.0.1:'+str(server.server_port)+'/index.html'
 try:
  run({'operation':'navigate','tab_id':tab,'expected_url':'about:blank','url':url})
  assert run({'operation':'fill','tab_id':tab,'expected_url':url,'selector':'#name','text':'sample'})['value']=='sample'
  assert run({'operation':'select','tab_id':tab,'expected_url':url,'selector':'#choice','value':'b'})['value']=='b'
  run({'operation':'click','tab_id':tab,'expected_url':url,'selector':'#go'})
  assert run({'operation':'observe','tab_id':tab})['title']=='sample'
  run({'operation':'download','tab_id':tab,'expected_url':url,'url':url.replace('index.html','sample.txt'),'destination':str(p/'download.txt')})
  assert (p/'download.txt').read_text()=='browser sample'
 finally:
  async def restore():
   b=Browser()
   try:
    await b.select_tab(tab);page=await b.connect();await page.goto('about:blank')
   finally: await b.disconnect()
  asyncio.run(restore());server.shutdown();server.server_close()
print('Real embedded browser form fill/select/click and download passed')
