"""Durable, bounded browser-goal check board. Actions remain local to Browser.
The board records intent and verified evidence, never replays inputs or credentials.
"""
from __future__ import annotations
import json
import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlsplit
from .config import STATE

ROLES=("entry","discover","act","final")
FEEDBACK=("off","finish","smart","each")
WORD_LOGIN=re.compile(r"login|log.in|sign.in|sign.on|התחבר|התחברות|כניסה|вход|войти|connexion|acceder",re.I)
WORD_SEARCH=re.compile(r"search|find|look.up|חפש|מצא|найди|поиск|chercher|recherche",re.I)
WORD_BUTTON=re.compile(r"login|sign.in|log.in|התחבר|כניסה|חשבון|войти|вход|connexion|sign in",re.I)
SECRET=re.compile(r"(?i)\b(password|passcode|token|secret|api[_-]?key|סיסמ[הא])\s*[:=]\s*\S+")

def clean(text,limit=350):
    value=SECRET.sub(r"\1=[REDACTED]",str(text or ""))
    value=re.sub(r"https?://\S+",lambda m:m.group(0).split("?")[0].split("#")[0],value)
    return value[:limit]

def infer(goal):
    value=str(goal or "")
    kind="login" if WORD_LOGIN.search(value) else "search" if WORD_SEARCH.search(value) else "general"
    link=re.search(r"https?://[^\s<>\"']+",value)
    host=urlsplit(link.group(0)).hostname if link else ""
    if not host and re.search(r"וואלה|\bwalla\b",value,re.I):host="walla.co.il"
    if not host and re.search(r"\bynet\b",value,re.I):host="ynet.co.il"
    return kind,host

def mode_steps(mode):
    """Small initial plan for non-browser tasks. No extra model roundtrip."""
    labels={
        "code":["Inspect source and tests","Identify a safe change","Implement and test","Verify actual tests and deployment evidence"],
        "desktop":["Inspect the active window","Find a verified control/path","Execute authorized input","Verify the resulting desktop state"],
        "inspect":["Identify the question and sources","Find grounded source evidence","Analyze the evidence","Verify an answer to the original question"],
    }
    titles=labels.get(mode,labels["inspect"])
    descriptions=["Observed starting state or source","Grounded route or relevant evidence",
                  "Actual action or analysis recorded","Final requested outcome established by evidence"]
    alternatives=[["Inspect current context","Find official or local source"],
                  ["Try another scoped source","Refine search"],
                  ["Try a safe observed alternative","On uncertain input, observe before retrying"],
                  ["Verify tests or resulting state","Report exact blocker if unverified"]]
    return [{"id":r,"role":r,"title":titles[i],"expected":descriptions[i],"alternatives":alternatives[i]}
            for i,r in enumerate(ROLES)]

def default_steps(kind):
    if kind=="login":
        return [
            {"id":"entry","role":"entry","title":"Reach the requested website","expected":"Requested site loaded with visible page evidence","alternatives":["Use official URL or observed site entry"]},
            {"id":"discover","role":"discover","title":"Find the sign-in entry point","expected":"A visible login/account entry point is identified","alternatives":["Header or primary navigation","Secondary menu or account icon","Footer or site search"]},
            {"id":"act","role":"act","title":"Open the login page","expected":"A dispatched input leads to a different observed page or modal","alternatives":["Try a different observed entry only after confirming the previous effect"]},
            {"id":"final","role":"final","title":"Verify the sign-in form is displayed","expected":"Fresh evidence of an actual sign-in form or recognized account entry screen; credentials not entered","alternatives":["Inspect form fields or sign-in modal; do not treat a homepage as completion"]},
        ]
    label="locate the requested information" if kind=="search" else "reach the requested target"
    return [
        {"id":"entry","role":"entry","title":"Reach the requested website","expected":"Relevant site or page opened and observed","alternatives":["Open official site","Use observed local entry point"]},
        {"id":"discover","role":"discover","title":"Find a route to "+label,"expected":"Target entry, link, menu or search path identified","alternatives":["Primary navigation","Secondary menu","Footer","Site search or another observed route"]},
        {"id":"act","role":"act","title":"Perform the selected site actions","expected":"Input was dispatched and its resulting page/state observed","alternatives":["Recover a fresh observation before any uncertain retry","Use a different observed path"]},
        {"id":"final","role":"final","title":"Verify the requested result","expected":"Fresh page evidence supports the original final goal, not just a page opening","alternatives":["Check exact target value/title in the destination","Report precise blocker if verification is impossible"]},
    ]

def seeded(goal,feedback_mode="smart",task_mode="browser"):
    kind,host=infer(goal)
    mode=task_mode if task_mode in ("browser","code","desktop","inspect") else "inspect"
    if mode!="browser":kind,host=mode,""
    return {"version":1,"intent":kind,"task_mode":mode,"target_host":host,"goal":clean(goal),
            "feedback_mode":feedback_mode if feedback_mode in FEEDBACK else "smart",
            "steps":default_steps(kind) if mode=="browser" else mode_steps(mode),"notes":"","created":time.time(),
            "last_editor":"local_template"}

def _result(a):
    return a.get("result") if isinstance(a.get("result"),dict) else {}

def _page(a):
    r=_result(a)
    if r.get("coherent") is True and (r.get("url") or r.get("title")):return r
    after=r.get("after")
    if isinstance(after,dict) and after.get("coherent") is True:return after
    return None

def _host_matches(url,host):
    if not host:return True
    try:
        actual=urlsplit(str(url or "")).hostname or ""
        return actual==host or actual.endswith("."+host)
    except ValueError:return False

def _login_form(page):
    controls=page.get("elements",page.get("controls",[]))
    account_entry=False
    for item in controls if isinstance(controls,list) else []:
        if not isinstance(item,dict):continue
        label=" ".join(str(item.get(k,"")) for k in ("name","placeholder","type","aria_label","autocomplete")).casefold()
        if "password" in label or "סיסמה" in label or "пароль" in label or "mot de passe" in label:
            return True
        if any(x in label for x in ("email","e-mail","username","user name","טלפון","טלפונ","אימייל","נייד","courriel","téléphone","логин","почта")):
            account_entry=True
    # Some modern sign-in screens begin with email or phone and reveal the
    # password later. Require explicit sign-in context, not an ordinary search box.
    page_context=str(page.get("url",""))+" "+str(page.get("title",""))
    return bool(account_entry and WORD_LOGIN.search(page_context))

def progress(board,actions,task_state=None):
    """Only observable evidence may earn a check mark."""
    if board.get("task_mode","browser")!="browser":
        return generic_progress(board,actions,task_state)
    steps=[dict(s, status="pending", evidence="") for s in board["steps"]]
    fresh=[(i,a,p) for i,a in enumerate(actions) if a.get("state")=="complete" and (p:=_page(a))]
    website=next(((i,a,p) for i,a,p in fresh
                  if _host_matches(p.get("url"),board.get("target_host"))),None)
    if website:
        for s in steps:
            if s["role"]=="entry":
                s.update(status="done",evidence="Observed target page: "+clean(website[2].get("title") or website[2].get("url"),120))
    recent_page=fresh[-1][2] if fresh else None
    matched_entry=None
    if board["intent"]=="login":
        for i,a,p in fresh:
            if not _host_matches(p.get("url"),board.get("target_host")):continue
            candidates=[c for c in p.get("elements",[]) if isinstance(c,dict) and WORD_BUTTON.search(c.get("name") or "")]
            if candidates:
                matched_entry=(i,candidates[0].get("name",""))
                break
    input_actions=[(i,a) for i,a in enumerate(actions) if a.get("tool") in ("browser_act","browser_pointer")
                   and _result(a).get("input_sent") is True]
    confirmed_input=None
    for i,action in input_actions:
        after=_result(action).get("after")
        observed_after=any(k>i for k,a,p in fresh)
        if (isinstance(after,dict) and after.get("coherent")) or observed_after:
            confirmed_input=(i,action)
    for s in steps:
        if s["role"]=="discover" and (matched_entry or confirmed_input):
            s.update(status="done",evidence=("Observed sign-in entry: "+clean(matched_entry[1],80)) if matched_entry else "Observed route and confirmed next browser state")
        if s["role"]=="act" and confirmed_input:
            s.update(status="done",evidence="Dispatched input followed by a new observed browser state")
    assessed=[_result(a) for a in actions if a.get("tool")=="browser_assess" and a.get("state")=="complete"]
    verified=bool(assessed and assessed[-1].get("verified") is True and assessed[-1].get("status")=="success")
    if verified and board["intent"]=="login":
        verified=bool(recent_page and _host_matches(recent_page.get("url"),board.get("target_host")) and _login_form(recent_page))
    for s in steps:
        if s["role"]=="final" and verified:
            s.update(status="done",evidence="Final browser assessment verified against observed destination")
    uncertain=any(a.get("state")=="pending" for a in actions)
    if not uncertain and input_actions and not confirmed_input:
        uncertain=True
    if not verified:
        pending=next((s for s in steps if s["status"]=="pending"),None)
        if pending:
            pending["status"]="uncertain" if uncertain else "active"
            pending["evidence"]="No confirmed post-input observation. Refresh evidence, never replay blindly." if uncertain else "Awaiting fresh observed evidence"
    # Visiting the requested homepage is provable from its matching observed URL.
    # Search/find tasks require their own final target evidence, not a homepage.
    goal_text=str(board.get("goal",""))
    simple_visit=bool(re.search(r"(?i)\b(?:open|visit|show)\b.*\b(?:homepage|home page|website|site)\b",goal_text))
    if task_state=="done" and board["intent"]!="login" and fresh and not input_actions and simple_visit and recent_page and _host_matches(recent_page.get("url"),board.get("target_host")):
        for s in steps:
            if s["status"]!="done":
                s.update(status="done",evidence="Completed read-only browser task with recorded page evidence")
    done=bool(steps and all(s["status"]=="done" for s in steps))
    mode=board["feedback_mode"]
    request_feedback=(mode=="each" and bool(actions)) or (mode=="finish" and done) or (mode=="smart" and uncertain)
    return {"steps":steps,"done":done,"uncertain":uncertain,"feedback_requested":request_feedback,
            "last_observed_host":(urlsplit(str(recent_page.get("url",""))).hostname if recent_page else None),
            "completed":sum(s["status"]=="done" for s in steps),"total":len(steps)}

def generic_progress(board,actions,task_state=None):
    steps=[dict(s,status="pending",evidence="") for s in board["steps"]]
    observed=[a for a in actions if a.get("state")=="complete"
              and isinstance(a.get("result"),dict) and not a["result"].get("error")]
    kinds={a.get("tool") for a in observed}
    if observed:steps[0].update(status="done",evidence="A source or target state was observed")
    if len(observed)>=2 or len(kinds)>=2:
        steps[1].update(status="done",evidence="A second source or state observation was recorded")
    operations={"file_write","file_patch","file_copy","terminal_run","terminal_command",
                "desktop_action","window_act","process_start","git_commit","candidate_test",
                "file_read","context_expand","context_search","project_context"}
    if any(a.get("tool") in operations for a in observed):
        steps[2].update(status="done",evidence="The action or analysis tool returned evidence")
    task_mode=board.get("task_mode","inspect")
    code_wrote=any(a.get("tool") in ("file_write","file_patch","candidate_patch") for a in observed)
    code_tested=any(a.get("tool")=="candidate_test" and _result(a).get("verified") is True for a in observed)
    desktop_changed=any(a.get("tool") in ("desktop_action","window_act") and _result(a).get("input_sent") is True for a in observed)
    desktop_reobserved=False
    for i,a in enumerate(actions):
        if a.get("tool") in ("desktop_action","window_act") and _result(a).get("input_sent") is True:
            if any(b.get("state")=="complete" and b.get("tool") in ("desktop_status","window_inspect") for b in actions[i+1:]):
                desktop_reobserved=True
    inspected=any(a.get("tool") in ("project_context","file_read","context_search") and (_result(a).get("path") or _result(a).get("items")) for a in observed)
    explicitly_verified=any(a.get("tool")=="task_verify" and _result(a).get("verified") is True and _result(a).get("goal_verified") is True and _result(a).get("original_goal")==board.get("goal") for a in observed)
    completed=bool(task_state=="done" and (explicitly_verified or
        (task_mode=="code" and code_wrote and code_tested) or
        (task_mode=="desktop" and desktop_changed and desktop_reobserved) or
        (task_mode=="inspect" and inspected)))
    if completed:
        for s in steps:
            s.update(status="done",evidence=s["evidence"] or "Final verified task result")
    uncertain=any(a.get("state")=="pending" for a in actions)
    if not completed:
        nxt=next((s for s in steps if s["status"]!="done"),None)
        if nxt:nxt.update(status="uncertain" if uncertain else "active",
                           evidence="Reobserve before acting" if uncertain else "Awaiting checked result")
    mode=board["feedback_mode"]
    review=(mode=="each" and bool(observed)) or (mode=="finish" and completed) or (mode=="smart" and uncertain)
    return {"steps":steps,"done":completed,"uncertain":uncertain,"feedback_requested":review,
            "completed":sum(s["status"]=="done" for s in steps),"total":len(steps)}

def guidance(board,actions,task_state=None):
    result=progress(board,actions,task_state)
    pending=next((s for s in result["steps"] if s["status"]!="done"),None)
    body={"kind":"browser_goal_check_board","original_goal_summary":board["goal"],
          "intent":board["intent"],"task_mode":board.get("task_mode","browser"),"target_host":board["target_host"],"feedback_mode":board["feedback_mode"],
          "completed":result["completed"],"total":result["total"],"steps":result["steps"],
          "next_step":pending,"uncertain":result["uncertain"],
          "requires_external_advice":result["feedback_requested"]}
    compact={"mode":body["task_mode"],"goal":body["original_goal_summary"],
             "completed":body["completed"],"total":body["total"],
             "next":body["next_step"],"finish":board["steps"][-1]["expected"],
             "uncertain":body["uncertain"],"advisor":body["feedback_mode"]}
    return (
        "TASK CHECK BOARD: "+json.dumps(compact,ensure_ascii=False,separators=(",",":"))
        +"\nAdvance the next logical stage without repeatedly replanning. V requires tool evidence. "
         "For uncertain input, reobserve/reconcile, never replay. On sites, begin at the entry page; try primary controls, secondary menus and footer links. Confirm the final state. "
         "Finish only after the original final goal is verified. External advice is optional, not execution. "
         "Use English operational instructions while preserving exact original-language names and UI labels."
    )

def validate_steps(raw):
    if not isinstance(raw,list) or not 3<=len(raw)<=8:raise ValueError("Provide 3–8 steps")
    seen=set();out=[]
    for i,s in enumerate(raw):
        if not isinstance(s,dict):raise ValueError("Invalid step")
        role=s.get("role")
        if role not in ROLES:raise ValueError("Invalid stage role")
        ident=str(s.get("id") or f"step{i}")
        if not re.fullmatch("[a-zA-Z0-9_-]{1,36}",ident) or ident in seen:raise ValueError("Duplicate/invalid step ID")
        seen.add(ident)
        title=str(s.get("title") or "").strip()
        expected=str(s.get("expected") or "").strip()
        if not title or len(title)>160 or not expected or len(expected)>240:raise ValueError("Step title/expected invalid")
        alternatives=s.get("alternatives",[])
        if not isinstance(alternatives,list) or len(alternatives)>6:raise ValueError("Too many alternatives")
        out.append({"id":ident,"role":role,"title":title,"expected":expected,
                    "alternatives":[str(x)[:160] for x in alternatives]})
    if out[0]["role"]!="entry" or out[-1]["role"]!="final" or not any(x["role"]=="act" for x in out):
        raise ValueError("Plan must start with entry, include action and end with final verification")
    return out

class BoardStore:
    def __init__(self,db_path=None):
        self.db_path=str(db_path or Path(STATE)/"hub.sqlite3")
    def _connect(self):
        conn=sqlite3.connect(self.db_path,timeout=15)
        conn.row_factory=sqlite3.Row
        conn.execute("CREATE TABLE IF NOT EXISTS browser_goal_boards(task_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, board TEXT NOT NULL)")
        return conn
    def ensure(self,task_id,goal,feedback_mode="smart",task_mode="browser"):
        b=seeded(goal,feedback_mode,task_mode)
        with self._connect() as con:
            con.execute("INSERT OR IGNORE INTO browser_goal_boards VALUES(?,?,?)",(task_id,1,json.dumps(b,ensure_ascii=False)))
        return self.read(task_id)
    def read(self,task_id):
        with self._connect() as con:
            r=con.execute("SELECT revision,board FROM browser_goal_boards WHERE task_id=?",(task_id,)).fetchone()
        return {**json.loads(r["board"]),"revision":r["revision"],"task_id":task_id} if r else None
    def update(self,task_id,expected_revision,*,steps=None,feedback_mode=None,notes=None,editor="user"):
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row=con.execute("SELECT revision,board FROM browser_goal_boards WHERE task_id=?",(task_id,)).fetchone()
            if row is None:raise KeyError("Browser board not found")
            if row["revision"]!=expected_revision:raise RuntimeError("Board revision conflict; refresh before editing")
            b=json.loads(row["board"])
            if steps is not None:b["steps"]=validate_steps(steps)
            if feedback_mode is not None:
                if feedback_mode not in FEEDBACK:raise ValueError("Invalid feedback mode")
                b["feedback_mode"]=feedback_mode
            if notes is not None:
                if len(str(notes))>1500:raise ValueError("Notes too long")
                b["notes"]=clean(notes,1500)
            b["last_editor"]=editor
            con.execute("UPDATE browser_goal_boards SET revision=?,board=? WHERE task_id=?",
                        (expected_revision+1,json.dumps(b,ensure_ascii=False),task_id))
        return self.read(task_id)
