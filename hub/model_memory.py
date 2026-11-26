"""Direct Ollama memory control, independent of inference."""
import httpx
import shutil
import subprocess
from .config import OLLAMA, STATE
from .model_placement import load_profiles, load_global, load_profile_overrides, resolve_profile, plan, recommend_context
from .model_settings import load_settings, save_settings

def matches(a,b):return a==b or a+':latest'==b or b+':latest'==a

async def status():
    async with httpx.AsyncClient(timeout=10,trust_env=False) as c:
        r=await c.get(OLLAMA+'/api/ps');r.raise_for_status()
    models=r.json().get('models',[]);selected=load_settings().model
    from .resources import Resources
    return {'selected_model':selected,'inference_enabled':load_settings().inference_enabled,'loaded':any(matches(m.get('name',''),selected) for m in models),'models':[{'name':m['name'],'size_vram':m.get('size_vram',0),'size':m.get('size',0),'size_ram':max(0,m.get('size',0)-m.get('size_vram',0)),'context_length':m.get('context_length')} for m in models],'profiles':{k:v.model_dump() for k,v in load_profiles(STATE).items()},'overrides':load_profile_overrides(STATE),'global_policy':load_global(STATE).model_dump(),'selected_effective_profile':resolve_profile(STATE, selected)[0].model_dump(),'resources':Resources().status()}

async def control(action,model=None):
    from .resources import Resources
    resources=Resources()
    with resources.owner(model or load_settings().model,'memory-'+action):
        result=await _control_owned(action,model)
        if result['verified'] and action in ('load','switch'):
            for name in result['targets']:resources.managed(name)
        return result



def _free_ram_bytes():
    try:
        import psutil
        return int(psutil.virtual_memory().available)
    except (ImportError, OSError, ValueError):
        return None


def _free_vram_bytes():
    executable = shutil.which('nvidia-smi')
    if not executable:
        return None
    try:
        output = subprocess.run(
            [executable, '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip().splitlines()
        return int(output[0].strip()) * (1024**2) if output else None
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


async def _load_options(client, name, settings, model_info):
    profile, provenance = resolve_profile(STATE, name)
    options = {'num_ctx': settings.context_tokens}
    tags = model_info
    size = next((int(m.get('size', 0)) for m in tags if matches(m.get('name',''), name)), 0)
    info = {}
    try:
        show = await client.post(OLLAMA+'/api/show', json={'model': name})
        show.raise_for_status()
        info = show.json().get('model_info') or {}
    except (httpx.HTTPError, ValueError, KeyError):
        # Do not pretend missing metadata permits an infinite context.
        info = {}
    blocks = next((int(v) for k, v in info.items()
                   if k.endswith('.block_count') and isinstance(v, (int, float))), None)
    native_context = next((int(v) for k, v in info.items()
                          if k.endswith('.context_length') and isinstance(v, (int,float))), None)
    free_vram = _free_vram_bytes()
    if profile.context_mode == 'manual':
        if native_context and profile.context_tokens > native_context:
            raise ValueError('Manual context exceeds the model advertised context')
        options['num_ctx'] = profile.context_tokens
        context_info = {'planned_context': options['num_ctx'], 'native_context': native_context,
                        'basis': 'explicit_model_override', 'verified': False}
    else:
        context_info = recommend_context(
            native_context=native_context, model_info=info, model_bytes=size,
            free_ram_bytes=_free_ram_bytes(), free_vram_bytes=free_vram,
            fallback_context=settings.context_tokens)
        options['num_ctx'] = context_info['planned_context']
    if profile.output_mode == 'manual':
        if profile.output_tokens > options['num_ctx'] - 256:
            raise ValueError('Manual output reservation exceeds available context; input and output share one window')
        output_ceiling = profile.output_tokens
    else:
        output_ceiling = max(256, options['num_ctx'] - 256)
    placement = {'mode': profile.mode, 'configuration_source': provenance,
                 'context_plan': context_info, 'output_ceiling': output_ceiling,
                 'memory_allocation_estimated': profile.mode != 'auto'}
    if profile.mode == 'cpu':
        options['num_gpu'] = 0
        placement['num_gpu'] = 0
    elif profile.mode != 'auto':
        if free_vram is None or not blocks:
            raise ValueError('Cannot verify available VRAM or model layers for requested manual GPU allocation')
        outcome = plan(profile, weight_bytes=size, free_vram_bytes=free_vram, layer_count=blocks)
        options['num_gpu'] = outcome['num_gpu']
        placement.update(outcome)
    return options, placement

async def _control_owned(action,model=None):
    if action not in ('load','unload','unload_all','switch'):raise ValueError('Invalid memory action')
    settings=load_settings();before=await status();target=model or settings.model
    placement=None
    async with httpx.AsyncClient(timeout=120,trust_env=False) as c:
        tags=await c.get(OLLAMA+'/api/tags');tags.raise_for_status()
        if action!='unload_all' and not any(matches(m['name'],target) for m in tags.json().get('models',[])):raise ValueError('Choose an installed model; this operation never downloads models')
        if action in ('load','switch'):
            conflicts=[m['name'] for m in before['models'] if not matches(m['name'],target) and not (action=='switch' and matches(m['name'],settings.model))]
            if conflicts:raise ValueError('Other models are resident; explicitly unload them before loading another model: '+', '.join(conflicts))
        if action=='switch' and not matches(settings.model,target) and before['loaded']:
            r=await c.post(OLLAMA+'/api/generate',json={'model':settings.model,'stream':False,'keep_alive':0});r.raise_for_status()
        targets=[m['name'] for m in before['models']] if action=='unload_all' else [target]
        for name in targets:
            payload={'model':name,'stream':False,'keep_alive':max(60,settings.keep_alive_minutes*60) if action in ('load','switch') else 0}
            if action in ('load','switch'):
                options,placement=await _load_options(c,name,settings,tags.json().get('models',[]))
                payload['options']=options
            r=await c.post(OLLAMA+'/api/generate',json=payload);r.raise_for_status()
    after=await status()
    present=lambda name:any(matches(m['name'],name) for m in after['models'])
    verified=all(present(n)==(action in ('load','switch')) for n in targets)
    if action in ('unload','unload_all') and verified:
        save_settings(settings.model_copy(update={'inference_enabled':False}))
        after=await status()
    if action in ('load','switch') and verified:
        saved_update={'model':target if action=='switch' else settings.model,'inference_enabled':True}
        # Legacy flat settings hold only the selected model's active runtime
        # allocation. Global/per-model policy is stored separately and remains
        # unchanged when the selected model switches.
        if placement and (action=='switch' or matches(settings.model,target)):
            active=next((m for m in after['models'] if matches(m['name'],target)),{})
            confirmed=active.get('context_length') or placement['context_plan']['planned_context']
            saved_update['context_tokens']=confirmed
            saved_update['response_tokens']=min(placement['output_ceiling'],max(256,confirmed-256))
        save_settings(settings.model_copy(update=saved_update))
        after=await status()
    return {'action':action,'targets':targets,'verified':verified,'memory':after,'placement':placement,'note':'No model files deleted. Local inference disabled until explicit load or switch.'}
