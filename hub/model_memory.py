"""Direct Ollama memory control, independent of inference."""
import httpx
from .config import OLLAMA
from .model_settings import load_settings, save_settings

def matches(a,b):return a==b or a+':latest'==b or b+':latest'==a

async def status():
    async with httpx.AsyncClient(timeout=10,trust_env=False) as c:
        r=await c.get(OLLAMA+'/api/ps');r.raise_for_status()
    models=r.json().get('models',[]);selected=load_settings().model
    from .resources import Resources
    return {'selected_model':selected,'inference_enabled':load_settings().inference_enabled,'loaded':any(matches(m.get('name',''),selected) for m in models),'models':[{'name':m['name'],'size_vram':m.get('size_vram',0),'size':m.get('size',0)} for m in models],'resources':Resources().status()}

async def control(action,model=None):
    from .resources import Resources
    resources=Resources()
    with resources.owner(model or load_settings().model,'memory-'+action):
        result=await _control_owned(action,model)
        if result['verified'] and action in ('load','switch'):
            for name in result['targets']:resources.managed(name)
        return result

async def _control_owned(action,model=None):
    if action not in ('load','unload','unload_all','switch'):raise ValueError('Invalid memory action')
    settings=load_settings();before=await status();target=model or settings.model
    async with httpx.AsyncClient(timeout=120,trust_env=False) as c:
        tags=await c.get(OLLAMA+'/api/tags');tags.raise_for_status()
        if action!='unload_all' and not any(matches(m['name'],target) for m in tags.json().get('models',[])):raise ValueError('Choose an installed model; this operation never downloads models')
        if action in ('load','switch'):
            conflicts=[m['name'] for m in before['models'] if not matches(m['name'],target) and not (action=='switch' and matches(m['name'],settings.model))]
            if conflicts:raise ValueError('Other models are resident; explicitly unload them before loading another model: '+', '.join(conflicts))
        if action in ('unload','unload_all'):
            settings=settings.model_copy(update={'inference_enabled':False});save_settings(settings)
        if action=='switch' and not matches(settings.model,target) and before['loaded']:
            r=await c.post(OLLAMA+'/api/generate',json={'model':settings.model,'stream':False,'keep_alive':0});r.raise_for_status()
        targets=[m['name'] for m in before['models']] if action=='unload_all' else [target]
        for name in targets:
            payload={'model':name,'stream':False,'keep_alive':max(60,settings.keep_alive_minutes*60) if action in ('load','switch') else 0}
            if action in ('load','switch'):payload['options']={'num_ctx':settings.context_tokens}
            r=await c.post(OLLAMA+'/api/generate',json=payload);r.raise_for_status()
    after=await status()
    present=lambda name:any(matches(m['name'],name) for m in after['models'])
    verified=all(present(n)==(action in ('load','switch')) for n in targets)
    if action in ('load','switch') and verified:
        save_settings(settings.model_copy(update={'model':target if action=='switch' else settings.model,'inference_enabled':True}))
        after=await status()
    return {'action':action,'targets':targets,'verified':verified,'memory':after,'note':'No model files deleted. Local inference disabled until explicit load or switch.'}
