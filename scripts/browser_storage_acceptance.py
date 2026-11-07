"""Real Qt restart test with synthetic cookies/storage; never reads user cookies."""
import json,os,subprocess,sys,tempfile,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def worker():
    from PySide6.QtCore import QTimer,QUrl
    from PySide6.QtWidgets import QApplication
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from hub.browser_profile import persistent_profile
    import shiboken6
    app=QApplication([])
    root=Path(sys.argv[2]);mode=sys.argv[3];url=sys.argv[4]
    profile=persistent_profile(None,root/'state',root/'cache')
    from PySide6.QtWebEngineCore import QWebEnginePage
    view=QWebEngineView();page=QWebEnginePage(profile,view);view.setPage(page)
    result={'ok':False,'error':'timed out'}
    script='''(async()=>{try{
      const mode=MODE;
      if(mode==='write')localStorage.setItem('persistent-test','local-ok');
      const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('test-storage',1);r.onupgradeneeded=()=>r.result.createObjectStore('values');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
      if(mode==='write')await new Promise((resolve,reject)=>{const tx=db.transaction('values','readwrite');tx.objectStore('values').put('idb-ok','test');tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error)});
      const value=await new Promise((resolve,reject)=>{const r=db.transaction('values').objectStore('values').get('test');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
      document.body.dataset.result=JSON.stringify({ok:true,local:localStorage.getItem('persistent-test'),indexeddb:value,cookie:document.cookie,httpOnlySeen:document.body.dataset.httponly==='true'});db.close();
    }catch(e){document.body.dataset.result=JSON.stringify({ok:false,error:String(e)})}})();'''.replace('MODE',json.dumps(mode))
    def loaded(ok):
        if ok:page.runJavaScript(script)
    def received(value):
        if value:
            result.clear();result.update(json.loads(value));timer.stop();QTimer.singleShot(1200,app.quit)
    timer=QTimer();timer.timeout.connect(lambda:page.runJavaScript('document.body?.dataset.result||""',received));timer.start(200)
    page.loadFinished.connect(loaded)
    view.resize(800,600);view.show();page.setUrl(QUrl(url+'/'+mode))
    QTimer.singleShot(20000,app.quit)
    app.exec()
    shiboken6.delete(page);shiboken6.delete(profile)
    (root/(mode+'.json')).write_text(json.dumps(result))

def main():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            self.send_response(200);self.send_header('Content-Type','text/html')
            if self.path=='/write':
                self.send_header('Set-Cookie','persistent_test=persistent-ok; Max-Age=86400; Path=/; SameSite=Lax')
                self.send_header('Set-Cookie','session_test=session-ok; Path=/; SameSite=Lax')
                self.send_header('Set-Cookie','http_only_test=http-only-ok; HttpOnly; Path=/; SameSite=Lax')
            seen='http_only_test=http-only-ok' in self.headers.get('Cookie','')
            self.end_headers();self.wfile.write(('<html><body data-httponly="'+str(seen).lower()+'">Synthetic storage test</body></html>').encode())
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    root=Path(tempfile.mkdtemp(prefix='browser-storage-',dir='E:/AI/artifacts'))
    try:
        for mode in ('write','read'):
            run=subprocess.run([sys.executable,__file__,'--worker',str(root),mode,f'http://127.0.0.1:{server.server_port}'],capture_output=True,timeout=35,env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            assert run.returncode==0,run.stderr.decode(errors='replace')[-1500:]
        result=json.loads((root/'read.json').read_text())
        assert result['ok'] and result['local']=='local-ok' and result['indexeddb']=='idb-ok',result
        assert 'persistent_test=persistent-ok' in result['cookie'] and 'session_test=session-ok' in result['cookie'],result
        assert result['httpOnlySeen'] and 'http_only_test' not in result['cookie'],result
        report={'separate_process_restart':True,'persistent_cookie':True,'session_cookie':True,'http_only_cookie':True,'local_storage':True,'indexed_db':True,'test_profile':str(root)}
        Path('E:/AI/artifacts/browser-storage-acceptance.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
    finally:server.shutdown()

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--worker':worker()
    else:main()
