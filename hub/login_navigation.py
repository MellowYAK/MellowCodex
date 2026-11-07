"""Find a site's sign-in through observed UI links; never guess an endpoint."""
import asyncio,re
from urllib.parse import urlsplit
from .errors import ObservationError

LOGIN=re.compile(r'log[ -]?in|sign[ -]?in|התחבר|התחברות|כניסה|כניסת|הזדהות',re.I)
ACCOUNT=re.compile(r'my account|account|personal area|החשבון|אזור אישי|איזור אישי',re.I)
MENU=re.compile(r'^menu$|navigation|תפריט|ראשי',re.I)
SERVICE=re.compile(r'^mail$|webmail|דואר',re.I)
EXCLUDE=re.compile(r'profile|browser|microsoft|google|chrome|edge|פרופיל|דפדפן',re.I)

def requests_login(goal):
    objective=goal.split('Proposed next step')[0]
    return bool(LOGIN.search(objective) and re.search(r'תפתח|לפתוח|תמצא|תחפש|חפש|מצא|פתח|\b(?:open|find|locate)\b',objective,re.I) and not re.search(r"(?:אל|לא|don't|do not)\s+(?:תפתח|תחפש|פתח|open|find)",objective,re.I))

def candidates(observation):
    result=[]
    for e in observation.get('elements',[]):
        if e.get('type') not in ('Hyperlink','Button') or not e.get('enabled',True):continue
        name=e.get('name','');href=e.get('href','');url=urlsplit(href)
        path=url.path+' '+url.fragment
        if EXCLUDE.search(name):continue
        score=100 if LOGIN.search(name+' '+path) else 70 if ACCOUNT.search(name+' '+path) else 40 if MENU.search(name) else 10 if SERVICE.search(name) else 0
        if score:result.append({**e,'score':score})
    return sorted(result,key=lambda e:-e['score'])

def login_form(observation):
    fields=[e for e in observation.get('elements',[]) if e.get('type')=='Edit' and e.get('enabled',True)]
    password=any(e.get('password') for e in fields)
    identifier=any(re.search(r'username|user name|e.?mail|phone|mobile|טלפון|משתמש|דואר|מייל',e.get('name',''),re.I) for e in fields)
    buttons=[e for e in observation.get('elements',[]) if e.get('type')=='Button' and e.get('enabled',True) and not EXCLUDE.search(e.get('name',''))]
    if (password or identifier) and any(LOGIN.search(e.get('name','')) for e in buttons):return True
    # Identifier-first authentication has no password or "Sign in" button yet.
    # Require the actual address-bar route, not a link elsewhere on the page;
    # an email/Continue newsletter form alone is not evidence of authentication.
    addresses=[e.get('value','') for e in fields if re.search(r'address|location|כתובת',e.get('name',''),re.I)]
    auth_route=any(LOGIN.search(urlsplit(url).path+' '+urlsplit(url).fragment) for url in addresses if url.startswith(('https://','http://')))
    next_button=any(re.fullmatch(r'continue|next|המשך|הבא',e.get('name','').strip(),re.I) for e in buttons)
    return bool(identifier and auth_route and next_button)

class LoginNavigation:
    def __init__(self,runner,task,folder):self.runner=runner;self.task=task;self.folder=folder;self.steps=[]
    async def click(self,hwnd,observation,control):
        if self.runner.desktop.stopped:raise ObservationError('Execution stopped before input')
        from .preferences import load_input_mode
        from .config import STATE
        mode=load_input_mode(STATE)
        args={'observation_id':observation['id'],'ref':control['ref'],'action':'invoke'}
        if mode!='physical':
            try:
                result=await self.runner.accessibility.act(args)
                self.steps.append({'method':'accessibility','label':control['name'],'href':control.get('href')})
                return result
            except ObservationError as exc:
                if 'does not support direct' not in str(exc):raise
        if mode=='quiet':raise ObservationError('This control requires physical input; quiet mode is selected')
        self.runner.desktop.focus(hwnd)
        fresh=await self.runner.accessibility.inspect(hwnd)
        matches=[e for e in fresh['elements'] if e['name']==control['name'] and e['type']==control['type'] and e['bounds']==control['bounds']]
        if len(matches)!=1:raise ObservationError('The target control changed before the click; inspect again')
        bounds=matches[0]['bounds'];shot=self.runner.desktop.capture_target(hwnd,self.folder)
        self.runner.desktop.act({'action':'click','observation_id':shot['id'],'x':bounds['left']+bounds['width']//2,'y':bounds['top']+bounds['height']//2})
        self.steps.append({'method':'physical click on freshly verified control','label':control['name'],'href':control.get('href')})

    async def run(self,hwnd):
        from .preferences import load_input_mode
        from .config import STATE
        if load_input_mode(STATE)!='quiet':self.runner.desktop.focus(hwnd)
        # Optional owned popup surfaces are separate from the site's navigation.
        for w in self.runner.desktop.windows():
            if w['hwnd']==hwnd or not self.runner.desktop._owned_by(w['hwnd'],hwnd):continue
            if re.search(r'save|unsaved|changes|permission|שמור|שינויים|הרשא',w['title'],re.I):continue
            popup=await self.runner.accessibility.inspect(w['hwnd'])
            close=[e for e in popup['elements'] if e['type']=='Button' and e['name'].strip().lower() in ('close','dismiss','not now','סגור','סגירה','לא עכשיו')]
            if len(close)==1:await self.click(w['hwnd'],popup,close[0]);await asyncio.sleep(.2)
        seen=set();observation=await self.runner.accessibility.inspect(hwnd)
        for attempt in range(6):
            if login_form(observation):
                return {'login_form_verified':True,'inspection':observation,'steps':self.steps,'note':'Visible authentication fields and a sign-in/continue button were observed. No credentials entered.'}
            options=[e for e in candidates(observation) if (e['name'],e.get('href','')) not in seen]
            if not options:break
            target=options[0];seen.add((target['name'],target.get('href','')))
            await self.click(hwnd,observation,target)
            for _ in range(8):
                await asyncio.sleep(.4);observation=await self.runner.accessibility.inspect(hwnd)
                if login_form(observation):break
                # Stop waiting when the next navigation opportunity appears.
                if any((e['name'],e.get('href','')) not in seen for e in candidates(observation)):break
        return {'login_form_verified':login_form(observation),'inspection':observation,'steps':self.steps,'note':'Continue with the observed navigation if incomplete. Do not report that a login page opened without a visible form.'}
