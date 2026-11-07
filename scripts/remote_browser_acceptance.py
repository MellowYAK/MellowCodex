import asyncio,json,sys,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hub.browser import Browser
from hub.config import ARTIFACTS
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(b'''<html><title>Local Agent Live Browser Test</title><body style="background:#eaf4ff;font:24px Arial;padding:40px"><h1>Live browser verification</h1><input id="field" style="font:24px Arial"><button id="save" onclick="document.querySelector('#result').textContent=document.querySelector('#field').value">Save</button><p id="result"></p><div style="height:1600px;background:linear-gradient(#eaf4ff,#3175ba)">Scroll area</div></body></html>''')
async def main(url):
 b=Browser();await b.new_tab(url)
 tabs=await b.tabs();tab=next(t for t in tabs['tabs'] if t['url']==url)
 p=await b.select_tab(tab['id']);await p.wait_for_load_state('domcontentloaded')
 frame=await b.frame()
 import base64
 (ARTIFACTS/'remote-browser-fixture.jpg').write_bytes(base64.b64decode(frame['image'].split(',')[1]))
 box=await p.locator('#field').bounding_box()
 await b.remote_input({'frame_id':frame['id'],'action':'click','x':box['x']+20,'y':box['y']+10})
 await b.remote_input({'frame_id':frame['id'],'action':'text','text':'LIVE_BROWSER_OK'})
 frame=await b.frame();box=await p.locator('#save').bounding_box()
 await b.remote_input({'frame_id':frame['id'],'action':'click','x':box['x']+20,'y':box['y']+10})
 result=await p.locator('#result').inner_text();assert result=='LIVE_BROWSER_OK',result
 frame=await b.frame();await b.remote_input({'frame_id':frame['id'],'action':'scroll','amount':500});await asyncio.sleep(.3)
 scrolled=await p.evaluate('scrollY');assert scrolled>0
 report={'live_render':True,'typed_and_clicked':result,'scroll_y':scrolled,'width':frame['width'],'height':frame['height']}
 (ARTIFACTS/'remote-browser-acceptance.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
 await p.goto('about:blank');await b.disconnect()
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
try:asyncio.run(main(f'http://127.0.0.1:{server.server_port}/'))
finally:server.shutdown()
