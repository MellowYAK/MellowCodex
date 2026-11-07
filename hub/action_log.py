"""Evidence-based action history; never infer success from a returned call."""
from collections import Counter

def action_log(store, task_id):
    task=store.get(task_id);rows=[];failures=[];attempts=Counter()
    for action in store.actions(task_id):
        result=action.get('result') or {};tool=action['tool'];attempts[tool]+=1
        checks={k:v for k,v in result.items() if (k=='verified' or k.endswith('_verified')) and isinstance(v,bool)}
        reason=result.get('error') or result.get('reason')
        if action['state']=='pending':outcome='pending'
        elif result.get('error') or result.get('exit_code',0):outcome='failed'
        elif result.get('deferred'):outcome='deferred'
        elif any(v is False for v in checks.values()):outcome='verification_failed'
        elif checks and all(checks.values()):outcome='verified'
        else:outcome='returned_unverified'
        row={'action_id':action['id'],'started_at':action['created'],'tool':tool,'tool_attempt':attempts[tool],
             'arguments':action['args'],'outcome':outcome,'reason':reason,'verification':checks,
             'result':result,'follows_failure':failures[-1] if failures else None,
             'different_tool_after_failure':bool(failures and rows and rows[-1]['tool']!=tool)}
        rows.append(row)
        if outcome in ('failed','verification_failed'):failures.append(action['id'])
    return {'task_id':task_id,'state':task['state'],'goal':task['goal'],'result':task['result'],
            'summary':dict(Counter(row['outcome'] for row in rows)),'actions':rows,
            'interpretation':'Returned is not success. Verification is limited to explicit tool checks. A different tool after failure is only a possible workaround, not proof it solved the same problem. Arguments/results are evidence, not private model reasoning.'}
