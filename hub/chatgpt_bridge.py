"""Direct, visible ChatGPT web conversation bridge; no MCP or hidden HTTP API."""
import asyncio,json,time,re,hashlib
from pathlib import Path
from urllib.parse import urlsplit
from .browser import Browser
from .errors import ObservationError
from .config import STATE

STATE_JS=r'''() => {
 const visible=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'};
 const replies=[],users=[],user_messages=[];
 const idOf=e=>(e.getAttribute('data-message-id')||e.closest('[data-message-id]')?.getAttribute('data-message-id')||e.closest('[data-chatgpt-selection-message-id]')?.getAttribute('data-chatgpt-selection-message-id')||e.closest('[data-chatgpt-search-message-ids]')?.getAttribute('data-chatgpt-search-message-ids')||'').split(/\s+/)[0];
 const orderOf=e=>{const key=e.closest('[data-content-search-turn-key]')?.getAttribute('data-content-search-turn-key')||e.closest('[data-testid^="conversation-turn-"]')?.getAttribute('data-testid')||'';const m=key.match(/(?:fallback-turn-|conversation-turn-)(\d+)/);return m?Number(m[1]):null};
 // A turn key may belong to the first of consecutive user messages (status,
 // then result). Prefer the actual preceding user message in document order.
 const classic=[...document.querySelectorAll('[data-message-author-role="user"],[data-message-author-role="assistant"]')].filter(visible);
 const messages=classic.length?classic:[...document.querySelectorAll('[data-user-message-bubble],[data-markdown-text-style="assistant-message"]')].filter(visible);
 for(const e of messages){
   if(e.getAttribute('data-message-author-role')==='user'||e.hasAttribute('data-user-message-bubble')){const root=e.closest('[data-chatgpt-search-message-ids]')||e.closest('[data-testid^="conversation-turn-"]')||e;const images=[...root.querySelectorAll('img')].filter(i=>i.alt==='User attachment'||i.src.startsWith('blob:')).map(i=>({loaded:i.complete&&i.naturalWidth>0,width:i.naturalWidth,height:i.naturalHeight}));const files=[...root.querySelectorAll('button[class*="resource-card"][aria-label]')].map(n=>n.getAttribute('aria-label'));users.push(e.innerText);user_messages.push({id:idOf(e),text:e.innerText,order:orderOf(e),attachment_images:images,attachment_files:files})}
   else replies.push({id:idOf(e),text:e.innerText,user_index:users.length-1,user_id:user_messages.at(-1)?.id||e.closest('[data-turn-key]')?.getAttribute('data-turn-key')||'',order:orderOf(e),code_blocks:[...e.querySelectorAll('pre')].map(c=>c.innerText)});
 }
 const editors=[...document.querySelectorAll('#prompt-textarea,[data-composer-markdown][contenteditable="true"]')].filter(visible);
 const composer=editors.length===1?editors[0]:null;
 const generating=[...document.querySelectorAll('[data-testid="stop-button"],button[aria-label="Stop generating"],button[aria-label="Stop response"]')].some(visible);
 const overlay=[...document.querySelectorAll('[role="dialog"],[role="menu"],[aria-modal="true"]')].some(visible);
 const login_required=[...document.querySelectorAll('button,a')].filter(visible).some(e=>/^(log in|sign in|התחבר|התחברות)$/i.test((e.innerText||e.getAttribute('aria-label')||'').trim()));
 const conversation_load_error=!composer && [...document.querySelectorAll('p,div,span')].filter(visible).some(e=>e.children.length===0 && !e.closest('[data-message-author-role],[data-user-message-bubble],[data-markdown-text-style="assistant-message"]') && /^Could not load this ChatGPT conversation\.?$/i.test(e.innerText.trim()));
 return {url:location.href,title:document.title,replies,users,user_messages,composer:!!composer,login_required,conversation_load_error,draft:composer?.innerText||composer?.value||'',generating,overlay,send:!!document.querySelector('[data-testid="send-button"]')};
}'''

COMPOSER='#prompt-textarea:visible,[data-composer-markdown][contenteditable="true"]:visible'
SEND='[data-testid="send-button"]:visible,button[aria-label="Send message"]:visible,button[aria-label="Send prompt"]:visible,button[aria-label="Send"]:visible,button[type="submit"]:visible'

def submitted_text_matches(expected, observed):
    """Match receipt, not byte equality: rich text changes code/link rendering.

    Callers must also require a unique new message ID outside the send baseline.
    """
    # Inline code is rendered without its Markdown backticks in sent bubbles.
    expected=' '.join(expected.replace('`','').split());observed=' '.join(observed.replace('`','').split())
    if not expected:return False
    if expected in observed:return True
    if len(expected)>=240 and len(observed)>=240 and expected[:240]==observed[:240]:return True
    prefix=re.split(r'\s*(?:…|\.\.\.)\s*(?:Show more|הצג עוד|הצג יותר)\s*$',observed)[0]
    return prefix!=observed and len(prefix)>=160 and expected.startswith(prefix)

def action_from_reply(text):
    # ChatGPT's current code-block UI renders the language label as plain text.
    text=re.sub(r'^\s*JSON\s*\n(?=\s*\{)','',text,flags=re.IGNORECASE)
    match=re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```',text)
    try:value=json.loads(match.group(1) if match else text)
    except (ValueError,TypeError):return None
    action=value.get('local_agent_action') if isinstance(value,dict) else None
    if not isinstance(action,dict) or not isinstance(action.get('id'),str) or not isinstance(action.get('task'),str):return None
    if not 1<=len(action['id'])<=120 or not 1<=len(action['task'])<=12000:return None
    if 'mode' in action and action['mode'] not in ('inspect','code','desktop','browser'):return None
    return {'id':action['id'],'task':action['task'],**({'mode':action['mode']} if 'mode' in action else {})}

def image_delivery_ready(message,paths):
    """Verify loaded images and actual file cards on the new sent message.

    A file card proves attachment presence, not remote content integrity.
    """
    if not paths:return True
    message=message or {}
    image_paths=[p for p in paths if Path(p).suffix.lower() in ('.png','.jpg','.jpeg','.webp','.gif')]
    images=message.get('attachment_images',[])
    if sum(bool(i.get('loaded') and i.get('width',0)>0 and i.get('height',0)>0) for i in images)<len(image_paths):return False
    cards=list(message.get('attachment_files',[]))
    for path in paths:
        if path in image_paths:continue
        source=Path(path)
        pattern=re.compile(re.escape(source.stem)+r'(?:\s*\(\d+\))?'+re.escape(source.suffix),re.I)
        index=next((i for i,name in enumerate(cards) if pattern.fullmatch(name)),None)
        if index is None:return False
        cards.pop(index)
    return True

class SubmissionBlocked(ObservationError):
    """Observed preflight rejection, before editing or submitting the composer."""
    def __init__(self,reason,message):
        super().__init__(message)
        self.reason=reason


class ChatGPTBridge:
    def __init__(self,binding_path=None):
        self.browser=Browser();self.tab_id=None;self.pending=None;self.bound_url=None
        self._sync_signature=None;self._sync_activity=time.monotonic();self._sync_checked=time.monotonic()
        self._load_recovery={}
        self._restore_attempts={}
        self.binding_path=Path(binding_path or STATE/'chatgpt-tab.json');self.preferred_url=None
        try:
            saved=json.loads(self.binding_path.read_text(encoding='utf-8'))['url']
            if urlsplit(saved).hostname=='chatgpt.com':self.preferred_url=saved
        except (OSError,ValueError,KeyError):pass
    def save_binding(self,url):
        from .browser_profile import restorable_url
        self.preferred_url=restorable_url(url)
        self.binding_path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.binding_path.with_suffix('.tmp');temporary.write_text(json.dumps({'url':self.preferred_url}),encoding='utf-8');temporary.replace(self.binding_path)
    async def connect(self,tab_id=None,create=False):
        inventory=await self.browser.tabs()
        candidates=[t for t in inventory['tabs'] if urlsplit(t['url']).hostname=='chatgpt.com']
        # A reconnect is to the persisted conversation, never whichever tab is
        # currently active (or a homepage left behind by a navigation failure).
        target=self.bound_url or self.preferred_url
        if not tab_id and target and urlsplit(target).path.startswith('/c/'):
            matching=[t for t in candidates if t['url']==target]
            if matching:
                self._restore_attempts.pop(target,None)
                tab_id=next((t['id'] for t in matching if t['id']==self.tab_id),matching[0]['id'])
            else:
                now=time.monotonic();count,last=self._restore_attempts.get(target,(0,None))
                if count<2 and (last is None or now-last>=30):
                    self._restore_attempts[target]=(count+1,now)
                    await self.browser.new_tab(target)
                return {'connected':False,'tabs':candidates,'url':target,'reason':
                        'Restoring the original linked ChatGPT conversation; task and message history are preserved.' if count<2 else
                        'The original linked ChatGPT conversation is unavailable after two restore attempts. Its link and pending work are preserved; no other chat will be used.'}
        if not candidates and create:
            await self.browser.new_tab('https://chatgpt.com/')
            for _ in range(20):
                await asyncio.sleep(.5)
                candidates=[t for t in (await self.browser.tabs())['tabs'] if urlsplit(t['url']).hostname=='chatgpt.com']
                if candidates:break
        chosen=tab_id or self.tab_id
        if chosen and not tab_id and not any(t['id']==chosen for t in candidates):
            matching=[t for t in candidates if t['url']==self.preferred_url]
            if len(matching)==1:chosen=matching[0]['id']
        if not chosen and self.preferred_url:
            matching=[t for t in candidates if t['url']==self.preferred_url]
            if len(matching)==1:chosen=matching[0]['id']
            elif not create:return {'connected':False,'tabs':candidates,'reason':'Open the saved ChatGPT conversation or explicitly select a different tab.'}
        if chosen:
            candidate=next((t for t in candidates if t['id']==chosen),None)
            if not candidate:raise ObservationError('The connected ChatGPT tab was closed or changed. Reconnect explicitly.')
        elif len(candidates)==1:candidate=candidates[0]
        else:return {'connected':False,'tabs':candidates,'reason':'Select one ChatGPT tab, or open ChatGPT and sign in in the embedded browser.'}
        self.tab_id=candidate['id'];self.bound_url=candidate['url'] if '/c/' in candidate['url'] else None
        await self.browser.select_tab(self.tab_id)
        self.save_binding(candidate['url'])
        state=await self.read()
        if state.get('conversation_load_error'):
            retried=await self.recover_load_error(state)
            return {'connected':True,'tab_id':self.tab_id,'url':state['url'],'ready':False,'reason':
                    'ChatGPT could not load this conversation. Retrying the same saved page; no message was sent.' if retried else
                    'ChatGPT could not load this conversation. Automatic recovery is limited to two reloads per connection session; check access to this exact conversation. No task was replayed.'}
        if state.get('composer'):self._load_recovery.pop(state.get('url'),None)
        login_required=bool(state.get('login_required'))
        ready=bool(state['composer']) and not login_required
        reason=('ChatGPT shows a Log in control in the agent browser. Sign in in that tab before starting PLAY; no instructions were sent.' if login_required
                else '' if ready else 'Waiting for the page to finish loading or for you to complete login/verification in its tab.')
        draft_present=bool(state.get('draft','').strip());generating=bool(state.get('generating'))
        draft_source=self.identify_owned_draft(state['draft']) if draft_present and getattr(self,'identify_owned_draft',None) else None
        return {'connected':True,'tab_id':self.tab_id,'url':state['url'],'ready':ready,'login_required':login_required,'reason':reason,
                'draft_present':draft_present,'draft_source':draft_source,'generating':generating,'send_ready':ready and not draft_present and not generating}
    async def adopt_final_url(self,page,tab_id):
        from urllib.parse import unquote
        old=self.bound_url or self.preferred_url or ''
        if tab_id!=self.tab_id or '/c/local-chatgpt:' not in unquote(old) or not self.pending:return False
        parsed=urlsplit(page.url)
        if parsed.hostname!='chatgpt.com' or not parsed.path.startswith('/c/') or 'local-chatgpt:' in unquote(parsed.path):return False
        state=await asyncio.wait_for(page.evaluate(STATE_JS),8)
        expected=self.pending.get('text','')
        matches=[m for m in state.get('user_messages',[]) if m.get('id') and m['id'] not in self.pending.get('user_ids',[]) and expected and submitted_text_matches(expected,m.get('text',''))]
        if len(matches)!=1:return False
        if getattr(self,'on_binding_changed',None):self.on_binding_changed(page.url)
        self.bound_url=page.url;self.save_binding(page.url)
        return True

    async def read(self):
        if not self.tab_id:
            if not self.preferred_url:raise ObservationError('Connect a ChatGPT tab first')
            restored=await self.connect()
            if not restored.get('connected'):raise ObservationError(restored.get('reason','Reconnect the saved ChatGPT conversation'))
        page=await self.browser.select_tab(self.tab_id)
        if urlsplit(page.url).hostname!='chatgpt.com':raise ObservationError('Connected tab is no longer on ChatGPT')
        if self.bound_url and page.url!=self.bound_url and not await self.adopt_final_url(page,self.tab_id):raise ObservationError('The connected ChatGPT conversation changed. Reconnect explicitly; no other conversation will be used.')
        if not self.bound_url and self.pending and '/c/' in page.url:
            self.bound_url=page.url;self.save_binding(page.url)
        return await asyncio.wait_for(page.evaluate(STATE_JS),8)

    async def changed_conversation(self):
        active=await self.browser.native_active_tab()
        if not active or urlsplit(active['url']).hostname!='chatgpt.com':return None
        if active['url']==(self.bound_url or self.preferred_url):return None
        page=self.browser.tab_refs[active['id']]
        if await self.adopt_final_url(page,active['id']):return None
        # Selecting a tab is not authorization to move a persistent handoff.
        # Explicit connect/select_context remains available for changing chats.
        return None

    async def recover_load_error(self,state):
        """Bounded recovery of a known error page, never authentication or sends."""
        page=self.browser.page
        if not self.bound_url or page.url!=self.bound_url:return False
        if not state.get('conversation_load_error') or any(state.get(k) for k in ('composer','generating','overlay','login_required')) or state.get('draft','').strip() or self.pending:return False
        now=time.monotonic()
        count,last=self._load_recovery.get(self.bound_url,(0,None))
        if count>=2 or (last is not None and now-last<30):return False
        fresh=await page.evaluate(STATE_JS)
        if not fresh.get('conversation_load_error') or any(fresh.get(k) for k in ('composer','generating','overlay','login_required')) or fresh.get('draft','').strip():return False
        self._load_recovery[self.bound_url]=(count+1,now)
        await page.reload(wait_until='domcontentloaded',timeout=15000)
        return True

    async def sync_if_idle(self,state,interval=30):
        """Refresh only the linked idle page to receive updates from other devices.

        This never changes the listener's message-ID cursor or sends a message.
        Normal reads continue every half second; reload is a bounded fallback for
        ChatGPT pages whose cross-device updates have stopped arriving.
        """
        if state.get('conversation_load_error'):return await self.recover_load_error(state)
        now=time.monotonic()
        signature=tuple((m.get('id'),m.get('text')) for m in state.get('user_messages',[]))+tuple((m.get('id'),m.get('text')) for m in state.get('replies',[]))
        if signature!=self._sync_signature:
            self._sync_signature=signature;self._sync_activity=now
        if state.get('generating') or state.get('overlay') or state.get('draft','').strip() or not state.get('composer'):
            self._sync_activity=now
            return False
        if now-max(self._sync_activity,self._sync_checked)<interval:return False
        page=self.browser.page
        if not self.bound_url or page.url!=self.bound_url:return False
        # Recheck immediately before navigation so a draft/generation that began
        # after the listener snapshot is preserved.
        fresh=await page.evaluate(STATE_JS)
        if fresh.get('generating') or fresh.get('overlay') or fresh.get('draft','').strip() or not fresh.get('composer'):return False
        if fresh.get('user_messages')!=state.get('user_messages') or fresh.get('replies')!=state.get('replies'):return False
        self._sync_checked=now
        await page.reload(wait_until='domcontentloaded',timeout=15000)
        return True

    async def open_conversation(self,url=None):
        inventory=await self.browser.tabs()
        matching=[t for t in inventory['tabs'] if url and t['url']==url]
        if len(matching)==1:
            self.tab_id=None;self.pending=None;self.bound_url=None
            result=await self.connect(matching[0]['id'])
            if not result.get('ready'):
                await self.browser.show_selected()
                raise ObservationError(result.get('reason') or 'The saved conversation is not ready; check its browser tab')
            return result
        before={t['id'] for t in inventory['tabs']}
        await self.browser.new_tab(url or 'https://chatgpt.com/')
        for _ in range(40):
            inventory=await self.browser.tabs()
            new=[t for t in inventory['tabs'] if t['id'] not in before and urlsplit(t['url']).hostname=='chatgpt.com']
            if len(new)==1:
                self.tab_id=None;self.pending=None;self.bound_url=None
                result=await self.connect(new[0]['id'])
                if result.get('login_required'):
                    await self.browser.show_selected()
                    raise ObservationError(result['reason'])
                if result['ready']:
                    await self.browser.show_selected();return result
            await asyncio.sleep(.5)
        raise ObservationError('The requested ChatGPT conversation is still loading; complete login if required in that tab')
    async def send(self,text,image_path=None,file_paths=None):
        state=await self.read()
        if state.get('login_required'):raise SubmissionBlocked('login_required','Sign in to ChatGPT in the agent browser before starting PLAY. No message was sent.')
        if not state['composer']:raise SubmissionBlocked('composer_unavailable','ChatGPT composer is unavailable. No message was sent.')
        if state['generating']:raise SubmissionBlocked('generating','ChatGPT is still generating a response. No message was sent.')
        if state['draft'].strip():raise SubmissionBlocked('draft_present','ChatGPT has an unsent draft. It was preserved; no message was sent.')
        page=self.browser.page
        composer=page.locator(COMPOSER)
        self.pending={'url':state['url'],'replies':len(state['replies']),'users':len(state['users']),'sent_at':time.time(),'user_ids':[m['id'] for m in state.get('user_messages',[])],'reply_ids':[m['id'] for m in state['replies']],'text':text}
        if getattr(self,'on_outbound',None):self.on_outbound(text)
        attachment='not_requested'
        if image_path:
            from .screenshot_settings import prepare
            image_path=prepare(image_path, "chatgpt")
            text+='\nScreenshot may be scaled; report positions relative to the attached image dimensions.'
        paths=list(dict.fromkeys(str(Path(p).resolve()) for p in ([image_path] if image_path else [])+list(file_paths or [])))[:5]
        attachment_files=[]
        if paths:
            from .file_library import FileLibrary,MAX_UPLOAD
            library=FileLibrary()
            for path in paths:
                source=Path(path)
                try:
                    record=library.get(source.parent.name,ready=True)
                    if Path(record['path']).resolve()!=source:raise KeyError('Different path')
                except (KeyError,ValueError):
                    if source.stat().st_size>MAX_UPLOAD:raise ValueError('Attachment exceeds 100 MB')
                    record=library.import_bytes(source.name,source.read_bytes(),source='ChatGPT evidence')
                attachment_files.append({'id':record['id'],'name':record['name']})
        if paths:
            import mimetypes
            # Current ChatGPT can keep a hidden duplicate composer in the DOM.
            # Restrict uploads to the form containing the visible editor.
            form=composer.locator('xpath=ancestor::form[1]')
            inputs=form.locator('input[type=file]') if await form.count()==1 else page.locator('input[type=file]')
            suitable=[]
            for i in range(await inputs.count()):
                candidate=inputs.nth(i);accept=await candidate.get_attribute('accept') or ''
                tokens=[s.strip().lower() for s in accept.split(',') if s.strip()]
                def accepts(path):
                    mime=mimetypes.guess_type(path)[0] or 'application/octet-stream'
                    return not tokens or any(t in ('*','*/*',mime,Path(path).suffix.lower(),mime.split('/')[0]+'/*') for t in tokens)
                if await candidate.get_attribute('webkitdirectory') is not None:continue
                if len(paths)>1 and await candidate.get_attribute('multiple') is None:continue
                if all(accepts(path) for path in paths):suitable.append(candidate)
            general=[c for c in suitable if not (await c.get_attribute('accept') or '').strip()]
            if len(general)==1:suitable=general
            if len(suitable)==1:
                await suitable[0].set_input_files(paths);attachment='selected'
                text+='\nAttached local evidence files: '+', '.join(Path(p).name for p in paths)+'. Inspect the attachments before claiming their contents. The original files are attached to THIS user message. Do not invent sandbox:/mnt/data links or file IDs from local Windows paths. For download, direct the human to the actual attachment above; only provide another link if a real file tool created and verified it.'
            else:
                raise ObservationError('No unambiguous compatible upload input was available. No message or file was sent.')
        # Upload processing can resize a background Qt page to zero. Restore
        # the same page viewport before addressing the composer; never reupload.
        await self.browser.connect()
        await composer.fill(text,timeout=8000)
        send=page.locator(SEND)
        # React may mount the send control after the composer input event.
        # Wait for one enabled control, including the initially absent case.
        for _ in range(60):
            if await send.count()==1 and await send.is_enabled():break
            await asyncio.sleep(.5)
        if await send.count()!=1 or not await send.is_enabled():raise RuntimeError('Draft prepared but send button unavailable; inspect the ChatGPT tab before retrying')
        # Keyboard activation avoids pointer-stability waits on background Qt
        # tabs and uses normal browser input rather than an untrusted JS click.
        # Activate once; only a new matching message proves delivery.
        if getattr(self,'on_submission',None):self.on_submission()
        await send.press('Enter',timeout=8000)
        for _ in range(120):
            await asyncio.sleep(.25);latest=await self.read()
            if latest.get('user_messages'):
                matches=[m for m in latest['user_messages'] if m['id'] and m['id'] not in self.pending['user_ids'] and submitted_text_matches(text,m['text'])]
                sent=matches[0] if len(matches)==1 else None
                verified=bool(sent)
                if sent:self.pending['user_id']=sent['id']
            else:verified=not paths and len(latest['users'])>self.pending['users']
            if verified and paths:
                verified=image_delivery_ready(sent,paths)
                if verified:attachment='verified_image' if all(Path(p).suffix.lower() in ('.png','.jpg','.jpeg','.webp','.gif') for p in paths) else 'verified_attachment_presence'
            if verified:
                result={'sent':True,'pending':self.pending,'attachment':attachment,'files':[Path(p).name for p in paths],'attachment_files':attachment_files}
                if getattr(self,'on_delivery',None):self.on_delivery(result)
                return result
        raise RuntimeError('Message submission outcome unknown. Do not resend automatically; inspect the ChatGPT tab.')
    async def submit_owned_draft(self,expected):
        """Complete preparation only for an unchanged, fully owned draft."""
        await self.browser.connect()
        state=await self.read()
        if state.get('generating') or not state.get('composer'):return False
        if ''.join(state.get('draft','').split())!=''.join(expected.split()):return False
        page=self.browser.page
        await page.locator(COMPOSER).fill(expected,timeout=8000)
        send=page.locator(SEND)
        if await send.count()!=1 or not await send.is_enabled():return False
        if getattr(self,'on_submission',None):self.on_submission()
        await send.press('Enter',timeout=8000)
        return True  # Delivery is verified separately from a new message receipt.

    async def reply(self):
        state=await self.read()
        if state['generating'] or not state['replies']:return None
        reply=state['replies'][-1]
        if self.pending:
            if self.pending.get('reply_ids') and reply['id'] in self.pending['reply_ids']:return None
            if 'reply_ids' not in self.pending and len(state['replies'])<=self.pending['replies']:return None
        if not reply['text'].strip():return None
        return {**reply,'fingerprint':hashlib.sha256((state['url']+'\n'+reply['id']+'\n'+reply['text']).encode()).hexdigest(),'url':state['url'],'source':'Connected ChatGPT assistant reply'}
    async def ask(self,question,timeout=180,file_paths=None):
        if getattr(self,'auto_active',lambda:False)():raise ObservationError('This ChatGPT tab coordinates the current task. Finish the local step; feedback is sent automatically. Do not start a nested consultation.')
        if file_paths:await self.send(question,file_paths=file_paths)
        else:await self.send(question)
        if getattr(self,'on_consultation',None):self.on_consultation()
        return await self.wait_reply(timeout)

    async def wait_reply(self,timeout=180):
        started=time.monotonic();last=None;stable=0
        while time.monotonic()-started<timeout:
            await asyncio.sleep(.5)
            reply=await self.reply()
            if reply and reply['fingerprint']==last:stable+=1
            else:last=reply['fingerprint'] if reply else None;stable=0
            if reply and stable>=2:
                if self.pending.get('user_id') and reply.get('user_id')!=self.pending['user_id']:continue
                if getattr(self,'on_answer',None):self.on_answer(reply)
                return reply
        raise RuntimeError('ChatGPT reply is still pending. The question was sent; do not resend it.')
