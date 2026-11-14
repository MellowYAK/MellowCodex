from .config import UI_ORIGINS
"""Playwright attaches only to the application's Qt WebEngine on loopback."""
import asyncio
import json
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit
import httpx
import psutil
from PIL import Image
from .config import STATE,CDP_PORT
from .errors import ObservationError
from .browser_evidence import resolve_ref

SNAPSHOT_JS='''token => {
 const visible=e=>{const r=e.getBoundingClientRect(); const s=getComputedStyle(e);return r.width>0&&r.height>0&&r.bottom>0&&r.right>0&&r.top<innerHeight&&r.left<innerWidth&&s.visibility!=='hidden'&&s.display!=='none'};
 const els=Array.from(document.querySelectorAll('a,button,input,textarea,select,img,video,audio,[role="button"],[role="link"],[contenteditable="true"]')).filter(e=>visible(e)||e.type==='file').slice(0,200);
 const elements=els.map((e,i)=>{const ref='e'+(i+1);e.setAttribute('data-local-agent-ref',token+'-'+ref); const r=e.getBoundingClientRect();return {ref,tag:e.tagName.toLowerCase(),role:e.getAttribute('role')||'',type:e.type||'',name:(e.getAttribute('aria-label')||e.labels?.[0]?.innerText?.split(String.fromCharCode(10))[0]||(e.tagName==='SELECT'?'':e.innerText)||e.getAttribute('placeholder')||e.getAttribute('name')||'').trim().slice(0,200),checked:(e.type==='checkbox'||e.type==='radio')?!!e.checked:undefined,focused:document.activeElement===e,enabled:!e.disabled&&e.getAttribute('aria-disabled')!=='true',modal:!!e.closest('[role=dialog],dialog[open],[aria-modal=true]'),options:e.tagName==='SELECT'?Array.from(e.options).slice(0,20).map(o=>({label:o.label,value:o.value,selected:o.selected})):undefined,options_truncated:e.tagName==='SELECT'&&e.options.length>20,value:e.type==='password'?'[private]':String(e.value||'').slice(0,150),href:e.tagName==='A'?e.href:undefined,x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)}});
 const links=Array.from(document.querySelectorAll('a[href]')).filter(e=>e.querySelector('h1,h2,h3,h4')||e.closest('main,article,[role="main"]')).map(e=>({name:(e.innerText||e.getAttribute('aria-label')||'').trim().slice(0,180),href:e.href})).filter(e=>e.name&&/^https?:/.test(e.href)).filter((e,i,a)=>a.findIndex(x=>x.href===e.href)===i).slice(0,60);
 return {url:location.href,document_generation:performance.timeOrigin,title:document.title,headings:Array.from(document.querySelectorAll('h1,h2,h3,[role=heading]')).filter(visible).map(e=>({text:(e.innerText||e.textContent||'').trim().slice(0,220),level:Number(e.getAttribute('aria-level'))||Number(e.tagName.slice(1))||null,in_navigation:!!e.closest('nav,[role=navigation]')})).filter(e=>e.text).slice(0,12),search_scope:'viewport',viewport:{x:globalThis.scrollX||0,y:globalThis.scrollY||0,width:innerWidth,height:innerHeight,document_height:document.documentElement?.scrollHeight||innerHeight},links,notices:Array.from(document.querySelectorAll('[role=alert],[role=status],[aria-live=assertive]')).filter(visible).map(e=>e.innerText.trim()).filter(Boolean).slice(0,8),text:(()=>{const root=document.querySelector('main,[role="main"]')||document.body;if(!document.createTreeWalker)return root?.innerText?.slice(0,4000)||'';const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let out='',n;while((n=w.nextNode())&&out.length<4000){const p=n.parentElement;if(p&&!p.closest('select,script,style')&&visible(p)){const r=document.createRange();r.selectNodeContents(n);const b=r.getBoundingClientRect();if(b.bottom>0&&b.top<innerHeight&&b.right>0&&b.left<innerWidth)out+=n.textContent.trim()+' ';}}return out.slice(0,4000);})(),elements,width:innerWidth,height:innerHeight};
}'''

CLICK_JS='''e => {
 if (!e.isConnected || e.disabled || e.getAttribute('aria-disabled')==='true')
   return {invoked:false,reason:'The observed control is detached or disabled'};
 e.scrollIntoView({block:'center',inline:'center',behavior:'instant'});
 const r=e.getBoundingClientRect(),s=getComputedStyle(e);
 if(!r.width||!r.height||s.visibility==='hidden'||s.display==='none')
   return {invoked:false,reason:'The observed control is no longer visible'};
 const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
 if(!hit || !(hit===e || e.contains(hit)))
   return {invoked:false,reason:'Another element covers the control; observe and dismiss the blocking overlay first'};
 e.click(); return {invoked:true};
}'''

class Browser:
    def __init__(self):
        self.playwright=None;self.connection=None;self.page=None;self.observation=None;self.instance=None;self.tab_refs={}
        self.target_id=None;self.recoveries={};self.last_recovery=None

    async def target_for(self,page):
        session=await asyncio.wait_for(page.context.new_cdp_session(page),4)
        try:return (await asyncio.wait_for(session.send('Target.getTargetInfo'),4))['targetInfo']['targetId']
        finally:
            try:await asyncio.wait_for(session.detach(),2)
            except Exception:pass

    async def targets(self):
        async with httpx.AsyncClient(timeout=3,trust_env=False) as client:
            response=await client.get(f'http://127.0.0.1:{CDP_PORT}/json/list');response.raise_for_status()
        return [t for t in response.json() if t.get('type')=='page' and not t['url'].startswith(UI_ORIGINS)]

    async def recover_target(self,target_id,reason):
        """Reload a renderer, never replay a click/submission or create another tab."""
        import websockets
        target=next((t for t in await self.targets() if t['id']==target_id),None)
        if not target:raise ObservationError('The requested browser tab was closed; no replacement was opened')
        if urlsplit(target['url']).scheme not in ('http','https'):
            raise ObservationError('Cannot automatically recover this page type')
        now=time.monotonic();attempts=[t for t in self.recoveries.get(target_id,[]) if now-t<120]
        if len(attempts)>=2:
            raise ObservationError('Browser renderer failed repeatedly: two recovery attempts in 120 seconds. Target '+target_id+'; last error: '+str(reason))
        attempts.append(now);self.recoveries[target_id]=attempts
        self.observation=None
        if len(attempts)>1:
            # A native Qt reload also clears Qt's crashed/frozen page lifecycle.
            import sys
            process=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.browser_ipc','--reload-target',target_id,target['url'],stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000000)
            out,err=await asyncio.wait_for(process.communicate(),8)
            result=json.loads(out) if out else {'error':err.decode(errors='replace') or 'No native reload response'}
            if result.get('error'):raise ObservationError('Native renderer recovery failed: '+result['error'])
        # Construct the loopback URL ourselves; never trust a returned websocket host.
        async with websockets.connect(f'ws://127.0.0.1:{CDP_PORT}/devtools/page/'+target_id,open_timeout=4,max_size=8*1024*1024) as socket:
            await socket.send(json.dumps({'id':1,'method':'Page.reload','params':{'ignoreCache':False}}) if len(attempts)==1 else json.dumps({'id':1,'method':'Runtime.enable'}))
            async with asyncio.timeout(12):
                while True:
                    response=json.loads(await socket.recv())
                    if response.get('id')==1:
                        if 'error' in response:raise ObservationError('Renderer reload failed: '+str(response['error']))
                        break
            # Reload acknowledgment precedes renderer readiness. Attaching again
            # immediately can reattach to the dying renderer and exhaust retries.
            async with asyncio.timeout(15):
                request_id=2
                while True:
                    await socket.send(json.dumps({'id':request_id,'method':'Runtime.evaluate','params':{'expression':'!!document.body && document.readyState !== "loading"','returnByValue':True}}))
                    while True:
                        response=json.loads(await socket.recv())
                        if response.get('id')==request_id:break
                    if response.get('result',{}).get('result',{}).get('value') is True:break
                    request_id+=1
                    await asyncio.sleep(.25)
        self.last_recovery={'target_id':target_id,'url':target['url'],'reason':str(reason),'attempt':len(attempts),'action':'reload_same_tab'}
        await self.disconnect();self.target_id=target_id
        await asyncio.sleep(.5)

    @staticmethod
    async def status():
        try:
            endpoint=json.loads((STATE/'browser-endpoint.json').read_text(encoding='utf-8'))
            if endpoint['url']!=f'http://127.0.0.1:{CDP_PORT}' or not psutil.pid_exists(endpoint['pid']):raise ValueError('Browser is not running')
            async with httpx.AsyncClient(timeout=2,trust_env=False) as client:
                response=await client.get(endpoint['url']+'/json/version');response.raise_for_status()
            return {'connected':True,'source':'embedded browser only, not Windows Chrome or Edge','engine':'Qt WebEngine','independent':True,'profile':endpoint['profile']}
        except Exception:
            return {'connected':False,'engine':'Qt WebEngine','independent':True,'reason':'Open the Local Agent desktop application to start its built-in browser'}

    @staticmethod
    async def extensions(action='status',extension_id=None,path=None):
        payload={'action':action,'extension_id':extension_id,'path':path}
        process=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.browser_ipc','--extensions',json.dumps(payload),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000000)
        try:stdout,stderr=await asyncio.wait_for(process.communicate(),12)
        except asyncio.TimeoutError:
            process.kill();await process.wait()
            raise RuntimeError('Extension operation outcome is unknown; read status before retrying')
        if process.returncode:raise RuntimeError('Built-in browser extension manager unavailable; open the desktop application')
        result=json.loads(stdout)
        if result.get('error'):raise ValueError(result['error'])
        return result

    async def connect(self,ready=True):
        from playwright.async_api import async_playwright
        try:
            endpoint=json.loads((STATE/'browser-endpoint.json').read_text(encoding='utf-8'))
            if endpoint['url']!=f'http://127.0.0.1:{CDP_PORT}' or not psutil.pid_exists(endpoint['pid']):raise ValueError('Desktop not running')
        except (OSError,ValueError,KeyError):
            raise RuntimeError('Internal desktop is unavailable. Call desktop_open with a stable request_id, verify ready=true, then retry this browser read. Do not repeat unchanged calls or invent URLs.')
        if self.instance is not None and self.instance!=endpoint['instance']:
            # Target IDs and observations belong to one desktop instance only.
            # The next read follows the new native selected tab; stale inputs
            # still fail fresh_page because their observation was invalidated.
            self.target_id=None;self.tab_refs={};self.observation=None
            self.recoveries={};self.last_recovery=None
        if self.connection and (not self.connection.is_connected() or self.instance!=endpoint['instance']):
            await self.disconnect()
        if not self.connection:
            self.playwright=await async_playwright().start()
            try:self.connection=await self.playwright.chromium.connect_over_cdp(endpoint['url'],timeout=10000,no_defaults=True)
            except BaseException:
                await self.playwright.stop();self.playwright=None;raise
            self.instance=endpoint['instance']
        # Tab inventory/switching must not depend on the current renderer being
        # healthy. A crashed tab must not prevent switching to a healthy one.
        if not ready:return None
        pages=[p for context in self.connection.contexts for p in context.pages if not p.is_closed() and not p.url.startswith(UI_ORIGINS)]
        if not pages:
            if self.target_id:
                await self.recover_target(self.target_id,'No live renderer');return await self.connect()
            raise RuntimeError('No browser tab is open')
        if not self.page or self.page.is_closed():
            self.page=pages[0]
            try:
                metadata=json.loads((STATE/'browser-tabs.json').read_text(encoding='utf-8'))
                active=self.target_id or next(t['target_id'] for t in metadata['tabs'] if t['selected'])
                found=False
                for candidate in pages:
                    target=await self.target_for(candidate)
                    if target==active:self.page=candidate;self.target_id=target;found=True;break
                if not found and any(t['id']==active for t in await self.targets()):
                    await self.recover_target(active,'Native tab exists but its renderer is unavailable to automation')
                    return await self.connect()
                if not found and self.target_id:raise ObservationError('Selected tab was closed; choose another tab explicitly')
            except (OSError,json.JSONDecodeError,KeyError,StopIteration):pass
        self.page.set_default_timeout(8000)
        self.target_id=await self.target_for(self.page)
        try:size=await asyncio.wait_for(self.page.evaluate('({width:innerWidth,height:innerHeight})'),6)
        except Exception as exc:
            if ('crash' in str(exc).lower() or isinstance(exc,TimeoutError)) and self.target_id:
                await self.recover_target(self.target_id,type(exc).__name__+': '+str(exc));return await self.connect()
            raise
        if not size['width'] or not size['height']:
            prepared=await self.prepare_hidden_target(self.target_id)
            await self.page.set_viewport_size({'width':(prepared or {}).get('width',1280),'height':(prepared or {}).get('height',800)})
        return self.page

    async def prepare_hidden_target(self,target_id):
        """Keep the application-owned page rendering without showing a window."""
        import sys
        process=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.browser_ipc','--prepare-target',target_id,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000000)
        try:out,err=await asyncio.wait_for(process.communicate(),8)
        except TimeoutError:
            process.kill();await process.wait();raise ObservationError('Native background page preparation timed out')
        result=json.loads(out) if out else {'error':err.decode(errors='replace') or 'No native page response'}
        if not result.get('prepared'):raise ObservationError(result.get('error','Native page was not prepared'))
        return result

    async def tabs(self):
        await self.connect(ready=False)
        pages=[p for c in self.connection.contexts for p in c.pages if not p.is_closed() and not p.url.startswith(UI_ORIGINS)]
        self.tab_refs={}
        for page in pages:
            target=await self.target_for(page)
            self.tab_refs[target]=page
        return {'source':'Local Agent embedded browser only','tabs':[{'id':t['id'],'url':t['url'],'title':t['title'],'available':t['id'] in self.tab_refs,'selected_by_agent':self.tab_refs.get(t['id']) is self.page} for t in await self.targets()]}

    async def select_tab(self,tab_id):
        inventory=await self.tabs()
        if tab_id not in self.tab_refs and any(t['id']==tab_id for t in inventory['tabs']):
            await self.recover_target(tab_id,'Selected tab renderer unavailable');await self.tabs()
        if tab_id not in self.tab_refs:raise ObservationError('Tab was closed or does not belong to this browser')
        self.page=self.tab_refs[tab_id];self.target_id=tab_id;self.observation=None
        # A hidden Qt tab can have a zero-sized viewport; validate the selected
        # page, not the previously selected page, before reading/filling controls.
        return await self.connect()

    async def native_active_tab(self):
        inventory=await self.tabs()
        try:
            metadata=json.loads((STATE/'browser-tabs.json').read_text(encoding='utf-8'))
            active=next(t['target_id'] for t in metadata['tabs'] if t['selected'])
        except (OSError,ValueError,KeyError,StopIteration):return None
        for entry in inventory['tabs']:
            if entry['id'] not in self.tab_refs:continue
            candidate=self.tab_refs[entry['id']];session=await candidate.context.new_cdp_session(candidate)
            try:target=(await session.send('Target.getTargetInfo'))['targetInfo']['targetId']
            finally:await session.detach()
            if target==active:return entry
        return None

    async def show_selected(self):
        import sys
        page=await self.connect();session=await page.context.new_cdp_session(page)
        try:target=(await session.send('Target.getTargetInfo'))['targetInfo']['targetId']
        finally:await session.detach()
        process=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.browser_ipc','--select-target',target,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000000)
        try:await asyncio.wait_for(process.communicate(),8)
        except TimeoutError:
            process.kill();await process.wait();raise ObservationError('Timed out showing the selected tab')
        if process.returncode:raise ObservationError('Unable to show the selected native tab')
        await asyncio.sleep(.2)

    async def close_tabs(self,tab_ids):
        import sys
        if not tab_ids or len(set(tab_ids))!=len(tab_ids):raise ValueError('Provide unique observed tab IDs')
        before=await self.tabs()
        known={t['id'] for t in before['tabs']}
        if not set(tab_ids)<=known:raise ObservationError('Unknown tab ID; obtain a fresh browser_tabs inventory')
        process=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.browser_ipc','--close-targets',json.dumps(tab_ids),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000000)
        try:out,err=await asyncio.wait_for(process.communicate(),8)
        except TimeoutError:
            process.kill();await process.wait();raise ObservationError('Close request timed out; inspect current tabs before retrying')
        result=json.loads(out) if out else {'error':err.decode(errors='replace')}
        if result.get('error'):raise ObservationError(result['error'])
        remaining=[]
        for _ in range(12):
            await asyncio.sleep(.25)
            after=await self.tabs()
            remaining=[t['id'] for t in after['tabs'] if t['id'] in tab_ids]
            if not remaining:break
        self.observation=None
        if self.target_id in tab_ids:self.page=None;self.target_id=None
        return {'closed_verified':not remaining,'closed_ids':[t for t in tab_ids if t not in remaining],'remaining_requested_ids':remaining,'tabs':after['tabs'],'note':'A blank start tab may remain. If requested tabs remain, inspect any unsaved-work prompt; no prompt was accepted automatically.'}

    async def new_tab(self,url):
        import sys
        if urlsplit(url).scheme not in ('http','https'):raise ValueError('Use an http(s) URL')
        process=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.browser_ipc',url,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000000)
        out,err=await process.communicate()
        if process.returncode:raise RuntimeError('Unable to open a native browser tab')
        await asyncio.sleep(.7)
        return await self.tabs()

    async def disconnect(self):
        # Stopping the client transport leaves the user's embedded browser open.
        if self.playwright:
            try:await asyncio.wait_for(self.playwright.stop(),5)
            except TimeoutError:pass
        self.playwright=None;self.connection=None;self.page=None;self.observation=None

    async def extract(self,observation_id,selector='body'):
        page=await self.fresh_page(observation_id)
        return await asyncio.wait_for(page.evaluate('''selector=>{
          const roots=[...document.querySelectorAll(selector)];
          return {url:location.href,title:document.title,count:roots.length,truncated:roots.length>100,
            nodes:roots.slice(0,100).map(root=>({tag:root.tagName,text:root.innerText?.slice(0,50000)||'',
              html:root.outerHTML.slice(0,50000),
              links:[...root.querySelectorAll('a[href]')].slice(0,500).map(a=>({text:a.textContent.trim(),url:a.href})),
              images:[...root.querySelectorAll('img')].slice(0,100).map(i=>({alt:i.alt,url:i.currentSrc||i.src})),
              tables:[...root.querySelectorAll('table')].slice(0,20).map(t=>[...t.rows].slice(0,200).map(r=>[...r.cells].map(c=>c.innerText)))
            }))};
        }''',selector),10)

    async def fresh_page(self,observation_id):
        page=await self.connect();obs=self.observation
        if not obs or obs['id']!=observation_id or obs['page'] is not page or obs['url']!=page.url or time.monotonic()-obs['at']>90:
            raise ObservationError('Observe this page again before using its content or scripts')
        if obs.get('coherent') is False or (obs.get('semantic_signature') and await self.semantic_signature(page)!=obs['semantic_signature']):
            raise ObservationError('Page content changed since the cited observation; observe again before acting or assessing.')
        return page

    async def script(self,observation_id,script,arguments=None):
        page=await self.fresh_page(observation_id)
        if not isinstance(script,str) or not 1<=len(script)<=20000:raise ValueError('Script must contain 1–20000 characters')
        self.observation=None
        # A script can have effects; never replay it on timeout/crash.
        result=await asyncio.wait_for(page.evaluate(script,arguments),12)
        encoded=json.dumps(result,ensure_ascii=False)
        return {'result':result if len(encoded)<=60000 else None,'truncated':len(encoded)>60000,'url':page.url,'note':'Script ran once. Observe again and verify its effects.'}

    async def observe(self,folder,query=""):
        page=await self.connect()
        token=uuid.uuid4().hex
        try:signature_before=await self.semantic_signature(page)
        except Exception:signature_before=None
        try:state=await asyncio.wait_for(page.evaluate(SNAPSHOT_JS,token),8)
        except Exception as exc:
            if ('crash' not in str(exc).lower() and not isinstance(exc,TimeoutError)) or not self.target_id:raise
            await self.recover_target(self.target_id,type(exc).__name__+': '+str(exc));return await self.observe(folder)
        from .browser_evidence import filter_controls
        state=filter_controls(state,query)
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        path=folder/('browser-'+token+'.png')
        capture={}
        try:
            await page.screenshot(path=str(path),timeout=2500)
            with Image.open(path) as picture:width,height=picture.size
            capture={'path':str(path),'width':width,'height':height}
        except Exception:
            capture={'screenshot_available':False,'observation_source':'live DOM','note':'Background renderer did not supply a screenshot. Use the observed DOM controls; do not infer visual details.'}
        try:signature_after=await self.semantic_signature(page)
        except Exception:signature_after=None
        coherent=bool(signature_before and signature_before==signature_after)
        if not coherent:
            # Never present pixels from a different semantic page as this snapshot.
            capture.pop('path',None)
            capture.update(screenshot_available=False,note='Page changed during capture; obtain a fresh observation before input or assessment.')
        self.observation={'semantic_signature':signature_after,'coherent':coherent,'id':token,'url':page.url,'at':time.monotonic(),'refs':{e['ref'] for e in state['elements']},'elements':state['elements'],'text':state['text'],'notices':state.get('notices',[]),'page':page}
        recovery=self.last_recovery;self.last_recovery=None
        from .browser_evidence import display_url
        # Keep full execution URLs in the private observation only.
        rendered={**state,'url':display_url(state.get('url',''))}
        rendered['elements']=[{**e,**({'href':display_url(e['href'])} if e.get('href') else {})} for e in state['elements']]
        rendered['links']=[{**link,'href':display_url(link.get('href',''))} for link in state.get('links',[])]
        return {**rendered,**capture,'coherent':coherent,'captured_at':time.time(),'tab_id':self.target_id,'frame_id':'main','page_signature':signature_after,'screenshot_observation_id':token if coherent and capture.get('path') else None,'recovery':recovery,'source':'Local Agent embedded Qt WebEngine (NOT Chrome, Edge, or another Windows app)','id':token,'left':0,'top':0}

    async def frame(self,_geometry_retry=True):
        import base64,sys
        page=await self.connect()
        if self.target_id:await self.prepare_hidden_target(self.target_id)
        capture_size=None
        try:
            pixels=await page.screenshot(type='jpeg',quality=75,timeout=1800)
            image='data:image/jpeg;base64,'+base64.b64encode(pixels).decode()
        except Exception:
            session=await page.context.new_cdp_session(page)
            try:target=(await session.send('Target.getTargetInfo'))['targetInfo']['targetId']
            finally:await session.detach()
            process=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.browser_ipc','--capture-target',target,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000000)
            out,err=await asyncio.wait_for(process.communicate(),8)
            if process.returncode:raise ObservationError('Browser renderer unavailable; open the Local Agent window and refresh')
            result=json.loads(out)
            if 'image' not in result:raise ObservationError(result.get('error','Browser renderer unavailable'))
            image=result['image']
            capture_size={'width':result['width'],'height':result['height']}
        size=await page.evaluate('({width:innerWidth,height:innerHeight})')
        if capture_size and capture_size!=size:
            self.remote_frame=None
            if not _geometry_retry:raise ObservationError('Browser capture geometry is unstable; no pointer frame issued')
            await page.set_viewport_size(capture_size)
            return await self.frame(_geometry_retry=False)
        # Normalize device pixels to CSS pixels so the visual model and pointer
        # share exactly the same coordinate space on high-DPI screens.
        from io import BytesIO
        raw=base64.b64decode(image.split(',',1)[1])
        with Image.open(BytesIO(raw)) as picture:
            if picture.size!=(size['width'],size['height']):
                output=BytesIO();picture.resize((size['width'],size['height']),Image.Resampling.LANCZOS).convert('RGB').save(output,'JPEG',quality=80)
                image='data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode()
        token=uuid.uuid4().hex
        self.remote_frame={'id':token,'page':page,'url':page.url,'at':time.monotonic(),**size}
        self.observation=None
        hints=await page.evaluate(SNAPSHOT_JS,token)
        text_regions=await page.evaluate('''() => Array.from(document.querySelectorAll('body *')).filter(e=>!e.children.length && e.textContent.trim() && !['SCRIPT','STYLE','NOSCRIPT'].includes(e.tagName)).map(e=>{const r=e.getBoundingClientRect();const s=getComputedStyle(e);return {text:e.textContent.trim().slice(0,160),x:r.x,y:r.y,width:r.width,height:r.height,visible:s.visibility!=='hidden'&&s.display!=='none'}}).filter(e=>e.visible&&e.width>0&&e.height>0&&e.x<innerWidth&&e.y<innerHeight&&e.x+e.width>0&&e.y+e.height>0).slice(0,80)''')
        for index,region in enumerate(text_regions):region['ref']='t'+str(index+1)
        self.remote_frame['regions']={r['ref']:r for r in [*hints.get('elements',[])[:60],*text_regions]}
        return {'id':token,'url':page.url,'title':await page.title(),'image':image,'coordinate_space':'CSS pixels; image dimensions match viewport','controls':hints.get('elements',[])[:60],'text_regions':text_regions,**size}

    async def remote_input(self,args):
        page=await self.connect();frame=getattr(self,'remote_frame',None)
        if not frame or args['frame_id']!=frame['id'] or frame['page'] is not page or frame['url']!=page.url or time.monotonic()-frame['at']>15:
            raise ObservationError('Browser frame changed; refresh before interacting')
        action=args['action']
        if action in ('click','move','drag'):
            x,y=args.get('x',-1),args.get('y',-1)
            def center(ref):
                region=frame.get('regions',{}).get(ref)
                if not region:raise ObservationError('Unknown frame region; obtain a fresh frame')
                return region['x']+region['width']/2,region['y']+region['height']/2
            if args.get('ref'):x,y=center(args['ref'])
            if not (0<=x<frame['width'] and 0<=y<frame['height']):raise ObservationError('Click is outside the displayed browser')
            button=args.get('button','left')
            if button not in ('left','right','middle'):raise ObservationError('Unknown virtual mouse button')
            if action=='drag':
                end_x,end_y=args.get('end_x',-1),args.get('end_y',-1)
                if args.get('end_ref'):end_x,end_y=center(args['end_ref'])
                if not (0<=end_x<frame['width'] and 0<=end_y<frame['height']):raise ObservationError('Drag endpoint is outside the displayed browser')
            self.remote_frame=None
            if action=='move':await page.mouse.move(x,y)
            elif action=='click':await page.mouse.click(x,y,button=button)
            elif self.target_id:
                import sys
                payload=dict(target_id=self.target_id,expected_url=page.url,x=x,y=y,end_x=end_x,end_y=end_y,button=button)
                process=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.browser_ipc','--virtual-drag',json.dumps(payload),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000000)
                try:out,err=await asyncio.wait_for(process.communicate(),8)
                except TimeoutError:
                    process.kill();await process.wait();raise RuntimeError('Virtual drag acknowledgement timed out; inspect current state before retrying')
                result=json.loads(out) if out else {'error':err.decode(errors='replace') or 'No virtual drag acknowledgement'}
                if not result.get('input_sent'):raise RuntimeError(result.get('error','Virtual drag outcome unknown'))
            else:
                session=await asyncio.wait_for(page.context.new_cdp_session(page),3)
                buttons={'left':1,'right':2,'middle':4}[button]
                async def dispatch(kind,px,py,pressed):
                    await asyncio.wait_for(session.send('Input.dispatchMouseEvent',{'type':kind,'x':px,'y':py,'button':button if kind!='mouseMoved' else 'none','buttons':buttons if pressed else 0,'clickCount':1 if kind!='mouseMoved' else 0}),3)
                try:
                    await dispatch('mouseMoved',x,y,False)
                    await dispatch('mousePressed',x,y,True)
                    for i in range(1,13):await dispatch('mouseMoved',x+(end_x-x)*i/12,y+(end_y-y)*i/12,True)
                finally:
                    try:await dispatch('mouseReleased',end_x,end_y,False)
                    finally:await asyncio.wait_for(session.detach(),3)
        elif action=='text':await page.keyboard.insert_text(args.get('text',''))
        elif action=='key':await page.keyboard.press(args['key'])
        elif action=='scroll':await page.mouse.wheel(0,max(-2000,min(2000,args.get('amount',0))))
        else:raise ObservationError('Unknown remote browser input')
        self.remote_frame=None
        return {'sent':True,'input_sent':True,'verification_required':True,'backend':'embedded-browser-virtual-input','physical_pointer_used':False,'note':'Input sent once; capture a fresh frame to verify its effect.'}

    async def observed_target(self,observation_id,ref):
        page=await self.connect();obs=self.observation
        if not obs or obs['id']!=observation_id or ref not in obs['refs'] or obs['page'] is not page or obs['url']!=page.url or time.monotonic()-obs['at']>90:
            raise ObservationError('Observe this browser tab again before choosing a file control')
        target=page.locator(f'[data-local-agent-ref="{obs["id"]}-{ref}"]')
        if await target.count()!=1:raise ObservationError('Observed control has changed')
        return target

    async def save_pdf(self,observation_id,name,share_with_chatgpt=False,layout='article'):
        from io import BytesIO
        from pypdf import PdfReader
        from .file_library import FileLibrary
        page=await self.connect();obs=self.observation
        if not obs or obs['id']!=observation_id or obs['page'] is not page or obs['url']!=page.url:
            raise ObservationError('Page changed. Observe the intended article before exporting.')
        if Path(name).name!=name or not name.lower().endswith('.pdf'):raise ValueError('Use a PDF filename without directories')
        await asyncio.wait_for(page.evaluate('document.fonts.ready.then(()=>true)'),8)
        # Capture the article before printing: some Qt builds crash the renderer
        # while printing complex pages. This read-only snapshot can still be exported.
        article=await asyncio.wait_for(page.evaluate('''()=>{
          const root=document.querySelector('h1')?.closest('article')||document.querySelector('article');
          if(!root)return null;
          return {url:location.href,title:root.querySelector('h1')?.textContent.trim(),paragraphs:[...root.querySelectorAll('p')].filter(p=>!p.closest('nav,aside,footer,form,[role="dialog"]')).map(p=>p.textContent.trim()).filter(Boolean)};
        }'''),8)
        if layout not in ('article','page'):raise ValueError('Choose article or page layout')
        if layout=='article' and article:
            from .article_pdf import render_article
            raw=await asyncio.to_thread(render_article,article)
            item=FileLibrary().import_bytes(name,raw,'application/pdf','Readable article: '+article['url'])
            return {**item,'pages':len(PdfReader(BytesIO(raw)).pages),'url':article['url'],'title':article['title'],'export_mode':'readable_article_text','note':'All extracted article paragraphs in a readable layout; excludes images, ads, navigation and interactive media. Inspect the generated PDF before delivery.','share_with_chatgpt':share_with_chatgpt,'verified_pdf':True}
        import sys
        process=await asyncio.create_subprocess_exec(sys.executable,'-m','hub.browser_ipc','--print-target',self.target_id,page.url,name,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000000)
        try:out,err=await asyncio.wait_for(process.communicate(),45)
        except TimeoutError:
            process.kill();await process.wait();raise ObservationError('Native PDF export timed out; inspect downloads before retrying')
        item=json.loads(out) if not process.returncode else {'error':'Native PDF export failed: '+err.decode(errors='replace')[-1000:]}
        export_mode='native_page';native_error=item.get('error')
        if not native_error and article:
            import pymupdf
            with pymupdf.open(item['path']) as printed:
                text=''.join(p.get_text() for p in printed)
            expected=sum(len(p.strip()) for p in article['paragraphs'])
            if len(text.strip())<max(200,expected*.7):
                native_error='Native print omitted the article text ('+str(len(text))+' characters for '+str(expected)+' source characters)'
                FileLibrary().fail(item['id'],native_error)
        if native_error:
            if not article:raise ObservationError(native_error+'; no article body is available for readable export')
            from .article_pdf import render_article
            raw=await asyncio.to_thread(render_article,article)
            item=FileLibrary().import_bytes(name,raw,'application/pdf','Readable article: '+article['url'])
            export_mode='readable_article_text'
        reader=PdfReader(item['path'])
        if not reader.pages:raise ValueError('Export produced no PDF pages')
        return {**item,'pages':len(reader.pages),'url':obs['url'],'title':article['title'] if article else page.url,'export_mode':export_mode,'native_error':native_error,'note':'Readable fallback preserves article text, not the original layout, images or interactive media.' if native_error else 'Native page print','share_with_chatgpt':share_with_chatgpt,'verified_pdf':True}

    async def upload(self,observation_id,ref,path):
        target=await self.observed_target(observation_id,ref)
        if await target.get_attribute('type')!='file':raise ObservationError('Choose an observed file upload input')
        path=Path(path).resolve()
        if not path.is_file():raise ValueError('Upload file is missing')
        await target.set_input_files(str(path))
        selected=await target.evaluate('(e)=>Array.from(e.files||[]).map(f=>({name:f.name,size:f.size}))')
        if not any(f['name']==path.name and f['size']==path.stat().st_size for f in selected):
            raise RuntimeError('Upload selection could not be verified; inspect the site before retrying')
        return {'selected':selected,'path':str(path),'note':'File selected in this site. Inspect the site to confirm processing or submission; selection alone does not prove completion.'}

    async def save_media(self,observation_id,ref):
        import base64,mimetypes
        from .file_library import FileLibrary,MAX_UPLOAD
        target=await self.observed_target(observation_id,ref)
        media=await target.evaluate('''async (e,limit)=>{
          if(!['IMG','AUDIO','VIDEO'].includes(e.tagName))throw Error('Choose an observed image, audio or video element');
          const src=e.currentSrc||e.src;if(!src)throw Error('No media source');
          const r=await fetch(src,{credentials:'include'});if(!r.ok)throw Error('Media fetch failed: '+r.status);
          if(Number(r.headers.get('content-length'))>limit)throw Error('Media exceeds 100 MB');
          const reader=r.body.getReader(),chunks=[];let size=0;
          while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>limit){await reader.cancel();throw Error('Media exceeds 100 MB')}chunks.push(value)}
          const blob=new Blob(chunks,{type:r.headers.get('content-type')||'application/octet-stream'});
          const data=await new Promise((resolve,reject)=>{const f=new FileReader();f.onload=()=>resolve(f.result.split(',')[1]);f.onerror=reject;f.readAsDataURL(blob)});
          return {data,mime:blob.type};
        }''',MAX_UPLOAD)
        suffix=mimetypes.guess_extension(media['mime'].split(';')[0]) or '.bin'
        return FileLibrary().import_bytes('browser-media'+suffix,base64.b64decode(media['data']),media['mime'],'saved browser media')

    async def navigate(self,url,folder):
        parts=urlsplit(url)
        if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password:
            raise ValueError('Use an http(s) URL without embedded credentials')
        page=await self.connect();self.observation=None
        try:await page.goto(url,wait_until='domcontentloaded',timeout=30000)
        except Exception as exc:
            if not any(word in str(exc).lower() for word in ('crash','err_connection','err_network','err_empty_response','timeout')):raise
            await self.recover_target(self.target_id,str(exc))
            page=await self.connect()
            await page.goto(url,wait_until='domcontentloaded',timeout=15000)
        return await self.observe(folder)

    async def semantic_signature(self,page):
        import hashlib
        state=await self.transition_state(page)
        return hashlib.sha256(json.dumps(state,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

    async def transition_state(self, page):
        """Read-only semantic state; excludes opaque URLs from returned evidence."""
        return await asyncio.wait_for(page.evaluate("""() => ({
            url:location.href, document_generation:performance.timeOrigin, ready:document.readyState,
            viewport:{x:scrollX,y:scrollY,width:innerWidth,height:innerHeight},
            text:(document.body?.innerText||'').slice(0,16000),
            values:[...document.querySelectorAll('input,textarea,select')]
                .filter(e=>e.type!=='password' && e.type!=='hidden')
                .slice(0,40).map(e=>[e.type,e.value,e.checked]),
            dialogs:[...document.querySelectorAll('[role=dialog],dialog[open]')]
                .map(e=>(e.innerText||'').slice(0,1000))
        })"""),2)

    async def settle_transition(self, page, before, pages_before, timeout=3.0):
        """Bounded cancellation-aware observation; never dispatches another input."""
        if before is None:
            return {'state':'unknown_effect','reason':'transition_probe_unavailable'}
        deadline=time.monotonic()+timeout;changed_at=None;previous=None
        while time.monotonic()<deadline:
            pages=list(page.context.pages) if getattr(page,'context',None) else []
            if any(p not in pages_before for p in pages):
                return {'state':'observed_transition','kind':'new_tab','select_tab_required':True}
            try:current=await self.transition_state(page)
            except Exception:
                await asyncio.sleep(.1)
                continue
            if current!=before and current.get('ready') in ('interactive','complete'):
                if current==previous and changed_at is not None and time.monotonic()-changed_at>=.2:
                    return {'state':'observed_transition','kind':'navigation' if current.get('url')!=before.get('url') else 'page_change'}
                if current!=previous:changed_at=time.monotonic()
            else:changed_at=None
            previous=current
            await asyncio.sleep(.1)
        return {'state':'dispatched_pending','reason':'No settled semantic transition observed before deadline; inspect destination before another input.'}

    async def act(self,args,folder):
        page=await self.connect();obs=self.observation
        action=args['action'];ref=args.get('ref')
        async def not_dispatched(code,message):
            self.observation=None
            result={'action':action,'input_sent':False,'dispatch_state':'not_dispatched',
                    'error':message,'error_code':code,'recoverable':True,'next_action':'Observe the fresh result and reselect; no input was sent.'}
            try:result['after']=await self.observe(folder)
            except Exception as exc:result['observation_error']=type(exc).__name__
            return result
        if not obs or obs['id']!=args['observation_id'] or time.monotonic()-obs['at']>90 or page is not obs['page'] or page.url!=obs['url']:
            return await not_dispatched('stale_observation','Browser observation expired or page changed. Use fresh evidence.')
        if action not in ('click','fill','press','select','check','scroll','back','forward'):
            return await not_dispatched('unsupported_action','Unsupported browser action; no input was sent.')
        try:await self.fresh_page(obs['id'])
        except ObservationError:
            return await not_dispatched('semantic_stale','Page content changed; select from the new observation.')
        target=None
        if action in ('click','fill','press','select','check'):
            try:ref=resolve_ref(obs,ref)
            except ObservationError as exc:
                return await not_dispatched('unresolved_target',str(exc))
            from .browser_workflow import retry_guard
            retry_guard(obs,ref)
            target=page.locator(f'[data-local-agent-ref="{obs["id"]}-{ref}"]')
            if await target.count()!=1 or not await target.is_visible():
                return await not_dispatched('target_changed','Element changed. Reselect from fresh evidence.')
        selected=next((e for e in obs.get('elements',[]) if e.get('ref')==ref),{})
        metadata={'requested':args.get('ref'),'resolved_ref':ref,'name':selected.get('name'),
                  'role':selected.get('role'),'observation_id':obs['id']}
        before=None
        if hasattr(page,'evaluate'):
            try:before=await self.transition_state(page)
            except Exception:pass
        pages_before=list(page.context.pages) if getattr(page,'context',None) else []
        self.observation=None
        try:
            if action=='click':
                invoked=await asyncio.wait_for(target.evaluate(CLICK_JS),8)
                if not invoked.get('invoked'):
                    return await not_dispatched('covered_or_disabled',invoked.get('reason','Control was not invoked'))
            elif action=='fill':
                if await target.get_attribute('type')=='password':
                    return await not_dispatched('personal_authentication_required','Enter the unavailable password directly in the built-in browser.')
                await target.fill(args.get('text',''))
            elif action=='press':await target.press(args['key'])
            elif action=='select':await target.select_option(label=args['text'])
            elif action=='check':await target.set_checked(args.get('checked',True))
            elif action=='scroll':await page.mouse.wheel(0,max(-1500,min(1500,args.get('amount',600))))
            elif action=='back':await page.go_back(wait_until='domcontentloaded',timeout=8000)
            elif action=='forward':await page.go_forward(wait_until='domcontentloaded',timeout=8000)
            else:raise ValueError('Unknown browser action')
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return {'action':action,'input_sent':None,'dispatch_state':'unknown_effect',
                    'error':'Input dispatch outcome is unknown; inspect destination before retrying.',
                    'exception_type':type(exc).__name__,'target':metadata,'retry_allowed':False}
        transition=await self.settle_transition(page,before,pages_before)
        result={'action':action,'input_sent':True,'verified':False,'target':metadata,
                'dispatch_state':transition['state'],'transition':transition,
                'note':'One input dispatched. Transition is not proof of task completion. Do not replay an uncertain effect.'}
        try:result['after']=await self.observe(folder)
        except Exception as exc:
            result.update(observation_error=type(exc).__name__,dispatch_state='unknown_effect')
        return result

    async def import_session(self,transfer):
        page=await self.connect()
        self.observation=None
        session=await page.context.new_cdp_session(page)
        await session.send('Page.enable')
        await session.send('Network.setCookies',{'cookies':transfer['cookies']})
        storage={key:transfer[key] for key in ('origin','localStorage','sessionStorage')}
        source='(()=>{const s='+json.dumps(storage)+';if(location.origin===s.origin){for(const [k,v] of Object.entries(s.localStorage))localStorage.setItem(k,v);for(const [k,v] of Object.entries(s.sessionStorage))sessionStorage.setItem(k,v);}})()'
        installed=await session.send('Page.addScriptToEvaluateOnNewDocument',{'source':source})
        try:
            await page.goto(transfer['url'],wait_until='domcontentloaded',timeout=30000)
            if await page.evaluate('location.origin')==transfer['origin']:
                await page.evaluate(source)
                await page.reload(wait_until='domcontentloaded')
        finally:
            await session.send('Page.removeScriptToEvaluateOnNewDocument',{'identifier':installed['identifier']})
        actual=(await session.send('Network.getCookies',{'urls':[transfer['url']]}))['cookies']
        await session.detach()
        transferred=sum(any(c['name']==expected['name'] and c['value']==expected['value'] and c['domain'].lstrip('.')==expected['domain'].lstrip('.') for c in actual) for expected in transfer['cookies'])
        return {'imported_cookies':transferred,'requested_cookies':len(transfer['cookies']),'local_storage_entries':len(transfer['localStorage']),'session_storage_entries':len(transfer['sessionStorage']),'skipped_partitioned':transfer['skipped_partitioned'],'url':page.url,'login_verified':False,'note':'Cookies were transferred; inspect the site to verify login. Some sites require reauthentication.'}
