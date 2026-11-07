"""Model-independent task state and actionable diagnostics."""
def task_status(store, task_id):
    task=store.get(task_id)
    events=store.events(task_id)
    relevant=[e for e in events if e['kind'] in ('model_start','tool_start','tool_result','unknown_action','background_replan','state')]
    last=relevant[-1] if relevant else None
    work=[e for e in relevant if e['kind']!='state']
    if task['state']=='running' and work:last=work[-1]
    unknown=store.latest_event(task_id,'unknown_action')
    actions=store.actions(task_id)
    errors=[a for a in actions if (a.get('result') or {}).get('error')]
    labels={'queued':'קיבלתי את המשימה; היא בתור לביצוע','running':'התחלתי לטפל במשימה','verifying':'בודק את התוצאה','waiting_review':'הביצוע הסתיים וממתין לבדיקת התוצאה','waiting_user':'המשימה נעצרה ונדרשת בדיקה','waiting_desktop':'ממתין לשולחן עבודה זמין','failed':'המשימה נכשלה','cancelled':'המשימה בוטלה','paused':'המשימה מושהית','done':'המשימה הושלמה'}
    text=labels.get(task['state'],task['state'])
    if task['state']=='running' and last:
        if last['kind']=='model_start':text='מטפל במשימה — ממתין לתשובת המודל'
        elif last['kind']=='tool_start':text='מבצע כעת: '+last['data']['name']
        elif last['kind']=='background_replan':text='שולחן העבודה אינו זמין; מחפש דרך להמשיך ברקע'
        elif last['kind']=='tool_result':text='התקבלה תוצאת כלי; בודק את הצעד הבא'
    blocked=task['state'] in ('waiting_user','failed','waiting_desktop','paused','cancelled')
    detail=unknown['data'] if unknown and any(a['id']==unknown['data'].get('action_id') and a['state']=='pending' for a in actions) else None
    if blocked:
        text+='\n'+task['result']
        if detail:text+='\nכלי: '+detail['name']+'\nשגיאה מדויקת: '+detail['error']+'\nתוצאת הפעולה אינה ודאית; אין לחזור עליה לפני בדיקת המצב בפועל.'
        elif errors:text+='\nכלי: '+errors[-1]['tool']+'\nשגיאה מדויקת: '+str(errors[-1]['result']['error'])
    from datetime import datetime,timezone
    now=datetime.now(timezone.utc)
    since=last['at'] if last else task['created']
    elapsed=max(0,int((now-datetime.fromisoformat(since)).total_seconds()))
    pending=[a for a in actions if a['state']=='pending']
    current=pending[-1] if pending and task['state']=='running' else None
    starts=[e for e in events if e['kind']=='model_start']
    phase=(last['kind'] if last else 'starting') if task['state']=='running' else task['state']
    wait_reason={'background_replan':'background_replanning','model_start':'model_inference','tool_start':'tool_execution','tool_result':'planning_next_step','queued':'executor_queue','waiting_user':'user_action_required','waiting_desktop':'interactive_desktop_required','waiting_review':'result_review'}.get(phase)
    live={'total_steps':None,'completed_actions':sum(a['state']=='complete' for a in actions),'phase':phase,'step':starts[-1]['data'].get('step') if starts else None,'waiting_for':wait_reason,'current_action':{'id':current['id'],'tool':current['tool'],'arguments':current['args']} if current else None,'last_action':{'id':actions[-1]['id'],'tool':actions[-1]['tool'],'state':actions[-1]['state'],'result':actions[-1].get('result')} if actions else None,'phase_elapsed_seconds':elapsed,'observed_at':now.isoformat(),'needs_poll':task['state'] in ('queued','running','verifying')}
    from .model_context import compact_result
    timeline=[]
    for action in actions[-12:]:
        result=action.get('result') or {}
        outcome='running' if action['state']=='pending' else 'deferred' if result.get('deferred') else 'failed' if result.get('error') or result.get('exit_code',0) else 'returned'
        timeline.append({'id':action['id'],'tool':action['tool'],'arguments':action['args'],'outcome':outcome,'result':compact_result(result),'expectation':'Command output and exit status, followed by verification of the requested effect' if action['tool'] in ('run_shell','terminal_start','terminal_read') else 'Tool result and evidence of the requested effect'})
    live['recent_actions']=timeline
    live['expectation']=timeline[-1]['expectation'] if current and timeline else 'Review returned evidence and choose the next step' if task['state']=='running' else None
    if task['state']=='running':text+=' · '+str(elapsed)+' שניות בשלב הנוכחי'
    return {'execution':live,'task_id':task_id,'state':task['state'],'text':text,'since':last['at'] if last else task['created'],'event_seq':last['seq'] if last else 0,'blocked':blocked,'diagnostics':{'result':task['result'],'unknown_action':detail,'actions':actions,'events':events}}
