"""Download original bytes, re-upload them, and verify rendered UI on a local fixture."""
import asyncio,base64,hashlib,io,json,sys,threading,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from hub.browser import Browser
from hub.file_library import FileLibrary
from hub.config import ARTIFACTS

buffer=io.BytesIO();Image.new('RGB',(70,40),(30,140,220)).save(buffer,format='PNG');DATA=buffer.getvalue()
uploaded=[]
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200)
        if self.path=='/original.png':
            self.send_header('Content-Type','image/png');body=DATA
        elif self.path=='/download':
            self.send_header('Content-Type','image/png');self.send_header('Content-Disposition','attachment; filename="verified-original.png"');body=DATA
        else:
            self.send_header('Content-Type','text/html; charset=utf-8')
            body=b'''<html><title>File transfer fixture</title><body style="font:24px Arial;background:#e3f4ff;padding:40px"><h1>Original file transfer</h1><a href="/download">Download original image</a><p><img src="/original.png"></p><label>Upload original <input id="upload" type="file" accept="image/png"></label><p id="result"></p><script>document.querySelector('#upload').onchange=async e=>{const r=await fetch('/upload',{method:'POST',body:e.target.files[0]});document.querySelector('#result').textContent=await r.text()}</script></body></html>'''
        self.end_headers();self.wfile.write(body)
    def do_POST(self):
        body=self.rfile.read(int(self.headers['Content-Length']));uploaded.append(body)
        self.send_response(200);self.end_headers();self.wfile.write(hashlib.sha256(body).hexdigest().encode())

async def run(url):
    browser=Browser();library=FileLibrary();before={f['id'] for f in library.list()}
    await browser.new_tab(url)
    inventory=await browser.tabs();tab=next(t for t in inventory['tabs'] if t['url']==url)
    page=await browser.select_tab(tab['id']);await browser.show_selected()
    try:
        obs=await browser.observe(ARTIFACTS/'files-acceptance')
        anchor=next(e for e in obs['elements'] if e.get('href')==url+'download')
        await browser.act({'observation_id':obs['id'],'ref':anchor['ref'],'action':'click'},ARTIFACTS/'files-acceptance')
        item=None
        for _ in range(50):
            item=next((f for f in library.list() if f['id'] not in before and f['name']=='verified-original.png' and f['status']=='ready'),None)
            if item:break
            await asyncio.sleep(.2)
        assert item,'Native download did not finish'
        assert Path(item['path']).read_bytes()==DATA
        obs=await browser.observe(ARTIFACTS/'files-acceptance');field=next(e for e in obs['elements'] if e['type']=='file')
        await browser.upload(obs['id'],field['ref'],item['path'])
        await page.wait_for_function('document.querySelector("#result").textContent.length===64')
        assert uploaded[-1]==DATA
        obs=await browser.observe(ARTIFACTS/'files-acceptance');media=next(e for e in obs['elements'] if e['tag']=='img')
        saved=await browser.save_media(obs['id'],media['ref']);assert Path(saved['path']).read_bytes()==DATA
        frame=await browser.frame();(ARTIFACTS/'file-transfer-live.jpg').write_bytes(base64.b64decode(frame['image'].split(',')[1]))
        report={'native_download':True,'original_bytes_preserved':True,'upload_received_by_site':True,'media_saved':True,'sha256':item['sha256'],'library_file_id':item['id'],'rendered_frame':True}
        (ARTIFACTS/'file-transfer-acceptance.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
    finally:
        await page.goto('about:blank');await browser.disconnect()

server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
try:asyncio.run(run(f'http://127.0.0.1:{server.server_port}/'))
finally:server.shutdown()
