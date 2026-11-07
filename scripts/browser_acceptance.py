"""Live built-in browser acceptance against a disposable local fixture."""
import asyncio,json,sys,threading,time
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hub.browser import Browser
from hub.session_transfer import validate_transfer
from hub.config import ARTIFACTS

HTML='''<!doctype html><meta charset="utf-8"><title>Local Agent Browser Test</title><style>body{font:24px Arial;background:#f2f4fc;padding:60px;color:#18213b}input,button{font:24px Arial;padding:12px;margin:10px}#result{padding:25px;background:white}label{display:block}</style><h1>Browser acceptance fixture</h1><label>Message <input aria-label="Message" id="message"></label><button id="save" onclick="document.querySelector('#result').textContent='Saved: '+document.querySelector('#message').value">Save message</button><p id="result">No message saved yet.</p><p id="session"></p><script>document.querySelector('#session').textContent='Session local storage: '+(localStorage.getItem('test-login')||'none');</script>'''
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        raw=HTML.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(raw)
    def log_message(self,*args):pass

async def run(url):
    folder=ARTIFACTS/'browser-acceptance';folder.mkdir(exist_ok=True)
    browser=Browser()
    try:
        state=await browser.navigate(url,folder)
        textbox=next(e['ref'] for e in state['elements'] if e['name']=='Message')
        result=await browser.act({'observation_id':state['id'],'action':'fill','ref':textbox,'text':'independent-browser-ok'},folder)
        state=result['after'];save=next(e['ref'] for e in state['elements'] if e['name']=='Save message')
        result=await browser.act({'observation_id':state['id'],'action':'click','ref':save},folder)
        assert 'Saved: independent-browser-ok' in result['after']['text']
        stale_rejected=False
        try:await browser.act({'observation_id':state['id'],'action':'click','ref':save},folder)
        except ValueError:stale_rejected=True
        assert stale_rejected
        transfer=validate_transfer({'url':url,'cookies':[{'name':'fixture_session','value':'synthetic-value-only','domain':'127.0.0.1','path':'/','httpOnly':True,'secure':False,'session':True,'sameSite':'lax'}],'localStorage':{'test-login':'synthetic-local-session'},'sessionStorage':{'session-only':'synthetic'}})
        imported=await browser.import_session(transfer)
        assert imported['imported_cookies']==1
        page=await browser.connect()
        assert await page.evaluate('localStorage.getItem("test-login")')=='synthetic-local-session'
        assert await page.evaluate('sessionStorage.getItem("session-only")')=='synthetic'
        await page.reload()
        assert await page.evaluate('localStorage.getItem("test-login")')=='synthetic-local-session'
        screen=await browser.observe(folder)
        report={'navigation':True,'fill':True,'click':True,'stale_observation_rejected':stale_rejected,'session_import':imported,'storage_verified':True,'after_reload_verified':True,'screenshot':screen['path']}
        (folder/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
    finally:await browser.disconnect()

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:asyncio.run(run(f'http://127.0.0.1:{server.server_port}/'))
    finally:server.shutdown()
