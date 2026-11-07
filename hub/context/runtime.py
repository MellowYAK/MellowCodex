"""Seed coding tasks with measured project context, recorded like other actions."""
import json
from ..i18n import t

async def prepare(engine,task,messages):
    if task['mode']!='code':return
    messages[0]['content']+='\n'+t('context.coding_instruction')
    async def read(name):
        action_id=engine.store.begin_action(task['id'],name,{})
        engine.store.event(task['id'],'tool_start',{'action_id':action_id,'name':name,'args':{},'origin':'context_bootstrap'})
        try:result=await engine.runner.execute(task,name,{})
        except Exception as exc:result={'error':str(exc)}
        if name=='project_context' and result.get('required_constraints'):
            # Required obligations belong to the fixed packet, not evictable history.
            messages[0]['content']+='\n'+t('context.required_packet')+'\n'+json.dumps(result['required_constraints'],ensure_ascii=False)
        engine.store.end_action(action_id,result)
        engine.store.event(task['id'],'tool_result',{'action_id':action_id,'name':name,'result':result,'origin':'context_bootstrap'})
        messages.extend([{'role':'assistant','tool_calls':[{'function':{'name':name,'arguments':{}}}]},
                         {'role':'tool','tool_name':name,'content':json.dumps(result,ensure_ascii=False)}])
        return result
    current=await read('project_context')
    if not current.get('error') and not current.get('index'):
        await read('context_refresh')
        await read('project_context')
