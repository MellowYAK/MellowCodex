"""Single-source model preference commands for HTTP, local chat and MCP.
Never bypasses owner permission controls or edits another chat's preferences.
"""
import json
import httpx
from pydantic import ValidationError
from .config import OLLAMA, STATE
from .model_settings import ModelSettings, load_settings, save_settings, field_metadata, parse_model_command

async def status():
    saved=load_settings(STATE)
    fields=field_metadata()
    result={'model':saved.model,'scope':'default','settings':saved.model_dump(),
            'metadata':fields,'runtime_available':False,'effective':None,
            'requested':saved.context_tokens,'reload_required':None,
            'scope_support':{'default':True,'conversation':False,'model':False},
            'context_distinction':{'context_tokens':'Ollama num_ctx model allocation',
                'response_tokens':'Ollama num_predict output limit',
                'conversation_budget':'prepared prompt compaction, not a change to Ollama num_ctx',
                'tool_output':'separate truncation/pagination and per-call transport limits'}}
    try:
        async with httpx.AsyncClient(timeout=7,trust_env=False) as c:
            ps=await c.get(OLLAMA+'/api/ps')
            ps.raise_for_status()
        models=ps.json().get('models',[])
        active=next((m for m in models if m.get('name') in (saved.model,saved.model+':latest') or
                     saved.model==m.get('name','')+':latest'),None)
        result['runtime_available']=True
        result['model_loaded']=bool(active)
        result['effective']=active.get('context_length') if active else None
        result['reload_required']=bool(active and active.get('context_length')!=saved.context_tokens)
        result['effective_source']='ollama:/api/ps' if active else 'model_not_loaded'
        if active and active.get('context_length') is None:
            result['reload_required']=None
    except (httpx.HTTPError,ValueError,KeyError) as exc:
        result['runtime_error']=type(exc).__name__
        result['effective_source']='runtime_unavailable'
    return result

async def perform(*,action='get',field=None,value=None,scope='default',text=None,busy=False,apply_now=False):
    if text is not None:
        parsed=parse_model_command(text)
        if parsed is None:
            return {'handled':False,'error':'Not a model preference command'}
        if parsed.get('action')=='error':
            return {'handled':True,'accepted':False,'error':parsed['error'],'field':parsed['field']}
        action=parsed['action'];field=parsed['field'];scope=parsed['scope'];value=parsed.get('value')
    if scope != 'default':
        return {'handled':True,'accepted':False,'scope':scope,'error':
                'Conversation/model overrides are not supported by the existing runner; no global settings were changed'}
    if action not in ('get','set','reset'):
        return {'handled':True,'accepted':False,'error':'Expected get, set or reset'}
    if field is not None and field not in field_metadata():
        return {'handled':True,'accepted':False,'error':'Unsupported model setting field','field':field}
    before=load_settings(STATE)
    if action!='get':
        if not field:
            return {'handled':True,'accepted':False,'error':'Specify a setting field'}
        if busy:
            return {'handled':True,'accepted':False,'error':'A task is active; no changes while inference is running'}
        desired=ModelSettings.model_fields[field].default if action=='reset' else value
        try:
            proposed=ModelSettings.model_validate({**before.model_dump(),field:desired})
        except ValidationError as exc:
            detail=exc.errors()[0]
            return {'handled':True,'accepted':False,'field':field,'requested':desired,
                    'error':f"Invalid setting: {detail.get('msg','validation failed')}"}
        if field in ('model','coding_model') and desired:
            try:
                async with httpx.AsyncClient(timeout=7,trust_env=False) as c:
                    r=await c.get(OLLAMA+'/api/tags');r.raise_for_status()
                installed={m.get('name') for m in r.json().get('models',[])}
                if desired not in installed:
                    return {'handled':True,'accepted':False,'field':field,'requested':desired,
                            'error':'The requested model is not installed'}
            except (httpx.HTTPError,ValueError) as exc:
                return {'handled':True,'accepted':False,'field':field,'requested':desired,
                        'error':'Could not verify installed models; original settings kept'}
        if field=='context_tokens':
            try:
                async with httpx.AsyncClient(timeout=8,trust_env=False) as c:
                    show=await c.post(OLLAMA+'/api/show',json={'model':proposed.model})
                    show.raise_for_status()
                native=[int(v) for k,v in (show.json().get('model_info') or {}).items()
                        if k.endswith('.context_length') and isinstance(v,(int,float))]
                advertised=max(native) if native else None
                if advertised and desired>advertised:
                    return {'handled':True,'accepted':False,'requested':desired,'model':proposed.model,
                            'native_context_length':advertised,'field':field,
                            'error':f'Model advertises context length {advertised}; requested {desired} is unsupported'}
            except (httpx.HTTPError,ValueError) as exc:
                return {'handled':True,'accepted':False,'requested':desired,'field':field,
                        'error':'Could not verify model capability with Ollama /api/show; original settings kept'}
        if proposed!=before:
            save_settings(proposed,STATE)
    actual=await status()
    answer={'handled':True,'accepted':True,'action':action,'field':field,
            'requested':before.model_dump().get(field) if action=='get' and field else
                        (actual['settings'].get(field) if field else None),
            'saved':actual['settings'].get(field) if field else actual['settings'],
            'model':actual['model'],'scope':'default',
            'effective':actual['effective'] if field in (None,'context_tokens') else actual['settings'].get(field),
            'effective_source':actual.get('effective_source'),
            'reload_required':actual['reload_required'] if field in (None,'context_tokens') else False,
            'runtime_available':actual['runtime_available'],
            'settings':actual['settings'],'metadata':actual['metadata']}
    if action!='get':
        answer['applies']='next_request'
        if apply_now and field=='context_tokens' and actual.get('model_loaded') and actual.get('reload_required'):
            # Reuse native managed model memory load operation, no private process or new runner.
            try:
                from .model_memory import control
                loaded=await control('load',actual['model'])
                after=await status()
                answer['effective']=after['effective']
                answer['reload_required']=after['reload_required']
                answer['runtime_verified']=bool(loaded.get('verified') and
                                                  after['effective']==after['settings']['context_tokens'])
                if not answer['runtime_verified']:
                    answer.update({'accepted':False,'error':'Ollama did not confirm the requested context; do not claim successful activation'})
            except Exception as exc:
                answer.update({'accepted':False,'error':'Runtime reload failed: '+str(exc)[:250],
                               'runtime_verified':False})
    return answer
