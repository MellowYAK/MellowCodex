"""Evidence-based browser workflow completion and bounded retry; no site selectors."""
import re,time,unicodedata,json
from .errors import ObservationError

FAILURE=re.compile(r"(?i)(?:connection|authentication|authorization|request|operation|link|sign.in).{0,30}(?:failed|failure)|something went wrong|an error occurred|access_denied|invalid_grant|לא הצליח|נכשל|שגיאת חיבור|ошибка|не удалось")
SUCCESS=re.compile(r"(?i)\b(?:connected|linked|saved|completed|successful|successfully|registered|published|updated|disconnected)\b|בהצלחה|מחובר|נשמר|הושלם|успеш|подключ[её]н|сохран")
NO_EFFECT=re.compile(r"(?i)not (?:connected|linked|saved|submitted|processed)|nothing (?:was )?(?:saved|changed|submitted)|no .{0,40}(?:was|were) (?:linked|connected|saved|created)|לא בוצע|לא נשמר|לא חובר|не подключ|не сохран")
RETRY=re.compile(r"(?i)^(?:try again|retry|reconnect|back|נסה שוב|ניסיון חוזר|חזרה|повторить|попробовать снова|назад)$")
MUTATIONS={'browser_act','browser_pointer','browser_upload','browser_script'}
PAGES={'browser_navigate','browser_select_tab','browser_observe',*MUTATIONS,'browser_assess'}

def norm(text):
 return ' '.join(unicodedata.normalize('NFC',str(text)).translate(dict.fromkeys(map(ord,'\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069'))).split())

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
  raise ObservationError('Evidence must be one exact quote (at least eight characters) from the cited observation. Put interpretation/translation in reason, not evidence. Observe again if the page changed; no success was recorded.')
 result={'status':status,'evidence':evidence,'reason':str(args.get('reason',''))[:600],
         'observation_id':page['id'],'checked_at':time.time(),'verified':False,'retry_allowed':False}
 if status=='success':
  result['verified']=not failure(page) and not NO_EFFECT.search(evidence) and bool(SUCCESS.search(evidence))
  result['next_step']='Finish with the observed result.' if result['verified'] else 'NOT COMPLETE: the quoted page does not establish the requested terminal result. Use the current observed controls to choose the remaining authorized action. Do not repeat this assessment or observe the unchanged page. Re-observe only if evidence is stale or the page changes. Do not repeat an uncertain prior input.'
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

def requires_outcome(action):
 # Scrolling only changes the view. It cannot prove or commit a business outcome.
 # Keep clicks, fills, submissions and uncertain writes under existing guards.
 if action.get('tool') not in MUTATIONS:return False
 result=action.get('result') or {}
 if result.get('input_sent') is False:return False
 if action.get('tool')=='browser_act' and (action.get('args') or {}).get('action',result.get('action'))=='scroll':return False
 return True

def completion_check(actions):
 changed=[i for i,a in enumerate(actions) if requires_outcome(a)]
 if not changed:
  # A rejected assessment cannot become success merely because no write occurred.
  # Pure read-only reports without an outcome claim keep their existing path.
  return False if any(a.get('tool')=='browser_assess' for a in actions) else None
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

def pending_effect_guard(actions):
 """An uncertain input requires destination reconciliation, never blind replay."""
 for index in range(len(actions)-1,-1,-1):
  action=actions[index];result=action.get('result') or {}
  if not requires_outcome(action) or not result:continue
  if result.get('dispatch_state') not in ('unknown_effect','dispatched_pending'):return None
  origin=None
  observation_id=(action.get('args') or {}).get('observation_id')
  for previous in reversed(actions[:index]):
   candidate=previous.get('result') or {};candidate=candidate.get('after',candidate)
   if isinstance(candidate,dict) and observation_id and candidate.get('id')==observation_id and candidate.get('coherent'):
    origin=candidate;break
  # Always compare the destination with the exact pre-input page, not with
  # the already changed after-page. A late screenshot can settle a transition.
  baseline=(origin or result.get('after') or {}).get('page_signature')
  for later in actions[index:]:
   evidence=later.get('result') or {}
   if later is not action and later.get('tool')=='browser_assess' and (evidence.get('verified') or evidence.get('retry_allowed')):return None
   page=evidence.get('after',evidence)
   if later.get('tool') in PAGES and isinstance(page,dict) and baseline and page.get('coherent') and page.get('page_signature') and page['page_signature']!=baseline:
    if origin and (page.get('id')==origin.get('id') or not origin.get('tab_id') or page.get('tab_id')!=origin.get('tab_id') or page.get('frame_id')!=origin.get('frame_id') or page.get('captured_at',0)<=origin.get('captured_at',0)):continue
    return None
  return {'input_sent':False,'dispatch_state':'not_dispatched','error_code':'unresolved_prior_effect','error':'Previous browser input has an uncertain outcome. Inspect destination and assess it before another mutation.','pending_action_id':action.get('id'),'retry_allowed':False}
 return None

def verify_outcome_freshness(page,result,actions):
 """Existing status text is not evidence that this task changed anything."""
 if result.get('status')!='success' or not result.get('verified'):return result
 mutations=[i for i,a in enumerate(actions) if requires_outcome(a)]
 if not mutations:return dict(result,verified=False,next_step='No operation evidence in this task. An existing status cannot prove a fresh change.')
 baseline=latest_page(actions[:mutations[0]])
 quote=norm(result.get('evidence','')).casefold()
 if not baseline or quote in page_text(baseline).casefold():
  return dict(result,verified=False,fresh_operation_verified=False,next_step='Outcome text was already present or no pre-operation baseline exists. Obtain a fresh source-backed operation receipt for the requested entity.')
 return dict(result,fresh_operation_verified=True)


def repeated_browser_reads(name,args,actions):
 if repeated_assessment(name,args,actions):return True
 # Bounded unchanged evidence, including the alternating tab/startup loop
 # observed during installed acceptance. Changed state permits progress.
 reads={'browser_observe','browser_tabs','agent_startup_status','agent_environment','recovery_context'}
 if name not in reads|{'browser_navigate'}:return False
 recent=[]
 for a in reversed(actions[-20:]):
  result=a.get('result') or {}
  if a.get('tool') in MUTATIONS and result.get('input_sent') is not False:break
  if a.get('tool') in ('browser_navigate','browser_select_tab') and a.get('state')=='complete' and not result.get('error'):break
  if a.get('tool')==name and a.get('args')==args and a.get('state') in ('complete','failed'):
   if name=='browser_navigate':
    # Retry only a bounded number of demonstrably failed navigations.
    # Unknown outcomes are handled by the pending-effect guard.
    if not result.get('error'):return False
    recent.append((result.get('exception_type'),result.get('error')))
   elif name=='browser_observe':
    signature=result.get('page_signature')
    if not signature:return False
    recent.append(signature)
   else:
    recent.append(json.dumps(result,sort_keys=True,default=str))
  if len(recent)==3:break
 return len(recent)==3 and recent[0]==recent[1]==recent[2]


def verification_focus(actions):
 # Only evidence of a performed operation permits the narrow verification stage.
 # An intermediate page, unknown effect, new navigation or write never triggers it.
 for index in range(len(actions)-1,-1,-1):
  action=actions[index];result=action.get('result') or {}
  if action.get('tool') in MUTATIONS|{'browser_navigate','browser_select_tab'}:return False
  if action.get('tool')!='browser_assess':continue
  if result.get('verified') is True:return False
  if result.get('fresh_operation_verified') is True and result.get('entity_verified') is False:
   page=latest_page(actions[index+1:])
   if page and norm(result.get('evidence','')).casefold() not in page_text(page).casefold():return False
   return True
 return False


def disclosed_browser_tools(names,actions,now=None):
 # This selects visible schemas, never grants authority or dispatches an input.
 visible=set(names)&{'desktop_open','desktop_status','browser_navigate','browser_observe','browser_assess','browser_act','browser_tabs','browser_select_tab','browser_close_tabs','tools_enable','chatgpt_ask','extensions_list','extension_run','agent_environment','conversation_history','action_routes'}
 if verification_focus(actions):return visible&{'browser_observe','browser_assess','tools_enable'}
 page=latest_page(actions)
 if not page or not page.get('coherent') or pending_effect_guard(actions):return visible
 age=(time.time() if now is None else now)-page.get('captured_at',0)
 if not 0<=age<60:return visible
 controls=[e for e in page.get('elements',[]) if e.get('enabled') and (e.get('tag') in ('button','input','select','textarea','a') or e.get('role') in ('button','link','checkbox'))]
 if controls and not SUCCESS.search(page_text(page)) and not failure(page):
  visible.discard('browser_assess')
 signature=page.get('page_signature');reads=0
 for action in reversed(actions):
  if action.get('tool') in MUTATIONS|{'browser_navigate','browser_select_tab'}:break
  result=action.get('result') or {}
  if action.get('tool')=='browser_observe' and signature and result.get('page_signature')==signature:reads+=1
 if controls and reads>=2:visible.discard('browser_observe')
 return visible


def assessment_entities(goal,evidence,actions):
 names=[];goal=norm(goal).casefold();evidence=norm(evidence).casefold()
 for action in actions:
  result=action.get('result') or {}
  if result.get('input_sent') is not True:continue
  name=norm((result.get('target') or {}).get('name',''))
  if 3<=len(name)<=120 and name.casefold() in goal and name.casefold() in evidence and name not in names:names.append(name)
 return names[:12]

def assessment_catalog(catalog,goal,actions):
 from copy import deepcopy
 page=latest_page(actions)
 choices=assessment_entities(goal,page_text(page or {}),actions)
 if not choices:return catalog
 out=[]
 for schema in catalog:
  if schema['function']['name']!='browser_assess':out.append(schema);continue
  schema=deepcopy(schema)
  prop=schema['function']['parameters']['properties'].get('entity')
  if prop is not None:
   prop['enum']=choices
   prop['description']='Choose one exact requested entity observed during this task. A generated receipt is not the requested entity.'
  out.append(schema)
 return out

def repeated_assessment(name,args,actions):
 if name!='browser_assess':return False
 key=(norm(args.get('entity','')),norm(args.get('evidence','')))
 count=0
 for action in reversed(actions):
  if action.get('tool') in MUTATIONS|{'browser_navigate','browser_select_tab'}:break
  if action.get('tool')!='browser_assess':continue
  result=action.get('result') or {};old=action.get('args') or {}
  if result.get('verified') is True:break
  if (norm(old.get('entity','')),norm(old.get('evidence','')))!=key:break
  count+=1
 return count>=3


def terminal_receipt(actions,now=None):
 """Conservative verification boundary, never proof of task completion."""
 page=latest_page(actions)
 if not page or not page.get('coherent'):return None
 age=(time.time() if now is None else now)-page.get('captured_at',0)
 if not 0<=age<=90:return None
 text=norm(page.get('text',''))
 if not 8<=len(text)<=1200 or not SUCCESS.search(text) or NO_EFFECT.search(text) or failure(page):return None
 # Intermediate forms/next buttons still require ordinary task planning.
 if any(e.get('enabled',True) and (e.get('tag') in ('button','input','select','textarea') or e.get('role') in ('button','checkbox','radio')) and e.get('width',0)>0 and e.get('height',0)>0 for e in page.get('elements',[])):return None
 evidence=verify_outcome_freshness(page,{'status':'success','verified':True,'evidence':text},actions)
 if not evidence.get('fresh_operation_verified'):return None
 return {'observation_id':page['id'],'evidence':text}

def terminal_message(actions,goal,now=None):
 receipt=terminal_receipt(actions,now)
 if not receipt:return None
 for action in reversed(actions):
  if action.get('tool')!='browser_assess':continue
  result=action.get('result') or {}
  if result.get('observation_id')!=receipt['observation_id']:continue
  if result.get('verified'):
   return {'role':'assistant','content':'Verified browser result: '+receipt['evidence']}
  return {'role':'assistant','content':'The page reports an operation result, but the requested entity or complete objective remains unverified. No further input was sent. Evidence: '+receipt['evidence']}
 entities=assessment_entities(goal,receipt['evidence'],actions)
 return {'role':'assistant','content':'Checking the fresh operation receipt before any further input.','tool_calls':[{'function':{'name':'browser_assess','arguments':{**receipt,'status':'success','entity':entities[0] if len(entities)==1 else '', 'reason':'Fresh terminal receipt after a recorded operation; independently verify requested entity and freshness. A receipt alone is not permission or complete-task proof.'}}}]}
