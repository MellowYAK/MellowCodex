"""Evidence-based browser workflow completion and bounded retry; no site selectors."""
import re,time
from .errors import ObservationError

FAILURE=re.compile(r"(?i)(?:connection|authentication|authorization|request|operation|link|sign.in).{0,30}(?:failed|failure)|something went wrong|an error occurred|access_denied|invalid_grant|לא הצליח|נכשל|שגיאת חיבור|ошибка|не удалось")
SUCCESS=re.compile(r"(?i)\b(?:connected|linked|saved|completed|successful|successfully|registered|published|updated|disconnected)\b|בהצלחה|מחובר|נשמר|הושלם|успеш|подключ[её]н|сохран")
NO_EFFECT=re.compile(r"(?i)not (?:connected|linked|saved|submitted|processed)|nothing (?:was )?(?:saved|changed|submitted)|no .{0,40}(?:was|were) (?:linked|connected|saved|created)|לא בוצע|לא נשמר|לא חובר|не подключ|не сохран")
RETRY=re.compile(r"(?i)^(?:try again|retry|reconnect|back|נסה שוב|ניסיון חוזר|חזרה|повторить|попробовать снова|назад)$")
MUTATIONS={'browser_act','browser_pointer','browser_upload','browser_script'}
PAGES={'browser_navigate','browser_select_tab','browser_observe',*MUTATIONS,'browser_assess'}

def norm(text):
 return ' '.join(str(text).split())

def page_text(page):
 return norm(' '.join(page.get('notices',[]))+' '+str(page.get('text','')))

def failure(page):
 text=norm(' '.join(page.get('notices',[]))) or page_text(page)
 return bool(FAILURE.search(text))

def assess(page,args,retry_count=0):
 status=args.get('status')
 if status not in ('success','failure','uncertain'):raise ObservationError('Use success, failure or uncertain.')
 evidence=norm(args.get('evidence',''))
 text=page_text(page)
 if len(evidence)<8 or evidence.casefold() not in text.casefold():
  raise ObservationError('Evidence must quote at least eight characters from current visible page text, not guessed success or button labels.')
 result={'status':status,'evidence':evidence,'reason':str(args.get('reason',''))[:600],
         'observation_id':page['id'],'checked_at':time.time(),'verified':False,'retry_allowed':False}
 if status=='success':
  result['verified']=not failure(page) and not NO_EFFECT.search(evidence) and bool(SUCCESS.search(evidence))
  result['next_step']='Finish with the observed result.' if result['verified'] else 'No terminal success evidence. Continue observing the destination and requested entity; a click, account selection or consent page is not completion.'
 elif status=='failure':
  retry_controls=[e for e in page.get('elements',[]) if e.get('enabled',True) and RETRY.fullmatch(norm(e.get('name','')))]
  safe=bool(failure(page) and NO_EFFECT.search(text) and retry_controls and args.get('reason') and retry_count<2)
  result.update(retry_allowed=safe,retry_refs=[e['ref'] for e in retry_controls] if safe else [])
  result['next_step']='One observed retry/back control is permitted. Re-observe every subsequent screen and verify the final destination.' if safe else 'Do not replay a possibly committed action. Inspect destination state or ask for help; no safe retry established, or retry budget exhausted.'
 else:result['next_step']='Observe without repeating the previous write; determine its effect before another attempt.'
 return result

def latest_page(actions):
 for a in reversed(actions):
  if a.get('tool') not in PAGES:continue
  r=a.get('result') or {};p=r.get('after',r)
  if isinstance(p,dict) and p.get('id') and 'elements' in p:return p
 return None

def completion_check(actions):
 changed=[i for i,a in enumerate(actions) if a.get('tool') in MUTATIONS]
 if not changed:return None
 for a in reversed(actions[changed[-1]+1:]):
  if a.get('tool') in ('browser_navigate','browser_select_tab'):return False
  if a.get('tool')=='browser_assess':
   r=a.get('result') or {}
   return r.get('status')=='success' and r.get('verified') is True and 0<=time.time()-r.get('checked_at',0)<=120
 return False

def retry_guard(observation,reference):
 if not observation or not failure(observation):return
 decision=observation.get('assessment',{})
 if not decision.get('retry_allowed') or reference not in decision.get('retry_refs',[]):
  raise ObservationError('Visible browser failure: use browser_assess with observed evidence before retry. If outcome may have committed, inspect destination instead of repeating input.')
