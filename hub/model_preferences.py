"""Single-source model preference commands for HTTP, local chat and MCP.
Never bypasses owner permission controls or edits another chat's preferences.
"""
import json
import httpx
from pydantic import ValidationError
from .config import OLLAMA, STATE
from .model_settings import ModelSettings, load_settings, save_settings, field_metadata, parse_model_command
from .model_placement import PlacementProfile, load_profiles, save_profile

async def status():
    saved=load_settings(STATE)
    fields=field_metadata()
    fields['placement_profile']={'type':'object','scope':['model'],'effect':'next_model_load','description':'Per-model auto/gpu/cpu/percent/layers placement; gpu_percent 0-100, gpu_layers; custom context/output.'}
    result={'model':saved.model,'scope':'default','settings':saved.model_dump(),
            'metadata':fields,'runtime_available':False,'effective':None,
            'requested':saved.context_tokens,'reload_required':None,
            'scope_support':{'default':True,'conversation':False,'model':True},
            'placement_profiles':{k:v.model_dump() for k,v in load_profiles(STATE).items()},
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
    if saved.browser_driver=='fara':
        from .fara import status as visual_status
    else:
        from .ui_tars import status as visual_status
    result['browser_driver']=saved.browser_driver
    result['browser_runtime']=await visual_status() if saved.browser_driver in ('ui_tars','fara') else {'selected':False}
    return result

async def perform(*,action='get',field=None,value=None,scope='default',text=None,busy=False,apply_now=False):
    if field=='global_policy':
        from .model_policy_service import perform as policy_perform
        return await policy_perform(action=action,value=value,busy=busy)
    if text is not None and field is None:
        from .model_profile_chat import apply as profile_chat_apply
        parsed_profile=await profile_chat_apply(text,busy=busy)
        if parsed_profile is not None:return parsed_profile

    if field=='placement_profile':
        if action not in ('get','set','reset'):
            return {'handled':True,'accepted':False,'error':'Expected get/set/reset for placement profile'}
        if action!='get' and busy:
            return {'handled':True,'accepted':False,'error':'A task is active; placement settings unchanged'}
        try:
            requested=json.loads(value) if isinstance(value,str) and value.startswith('{') else value
            if action=='get':
                name=requested if isinstance(requested,str) and requested else load_settings(STATE).model
                data=load_profiles(STATE).get(name,PlacementProfile())
                return {'handled':True,'accepted':True,'model':name,'placement_profile':data.model_dump(),'stored':name in load_profiles(STATE)}
            if not isinstance(requested,dict) or not isinstance(requested.get('model'),str):
                return {'handled':True,'accepted':False,'error':'Provide JSON {model, profile} with an installed exact model name'}
            name=requested['model']
            async with httpx.AsyncClient(timeout=8,trust_env=False) as client:
                response=await client.get(OLLAMA+'/api/tags')
                response.raise_for_status()
            installed={m.get('name') for m in response.json().get('models',[])}
            if name not in installed:
                return {'handled':True,'accepted':False,'error':'Choose an exact installed model ID'}
            profile=PlacementProfile() if action=='reset' else PlacementProfile.model_validate(requested.get('profile',{}))
            save_profile(STATE,name,profile)
            actual=load_profiles(STATE)[name]
            return {'handled':True,'accepted':True,'model':name,'placement_profile':actual.model_dump(),
                    'saved':True,'applies':'next_model_load',
                    'note':'Actual GPU VRAM/CPU RAM is measured after load; percentage is not exact VRAM.'}
        except (ValueError,TypeError,httpx.HTTPError,ValidationError) as exc:
            return {'handled':True,'accepted':False,'error':str(exc)[:400]}

    if text is not None:
        parsed=parse_model_command(text)
        if parsed is None:
            return {'handled':False,'error':'Not a model preference command'}
        if parsed.get('action')=='error':
            return {'handled':True,'accepted':False,'error':parsed['error'],'field':parsed['field']}
        if parsed['action']=='set_many':
            scope=parsed['scope']
            if scope!='default':
                return {'handled':True,'accepted':False,'scope':scope,
                        'error':'Conversation overrides are not supported; no settings changed'}
            if busy:
                return {'handled':True,'accepted':False,'error':'A task is active; no settings changed'}
            requested=parsed['fields']
            prior=load_settings(STATE)
            try:
                updated=ModelSettings.model_validate({**prior.model_dump(),**requested})
            except ValidationError as exc:
                return {'handled':True,'accepted':False,'requested':requested,
                        'error':f"Invalid setting: {exc.errors()[0].get('msg','validation failed')}"}
            try:
                async with httpx.AsyncClient(timeout=8,trust_env=False) as c:
                    show=await c.post(OLLAMA+'/api/show',json={'model':updated.model})
                    show.raise_for_status()
                native=[int(v) for k,v in (show.json().get('model_info') or {}).items()
                        if k.endswith('.context_length') and isinstance(v,(int,float))]
                advertised=max(native) if native else None
                if advertised and updated.context_tokens>advertised:
                    return {'handled':True,'accepted':False,'requested':requested,
                            'native_context_length':advertised,
                            'error':'Requested context exceeds advertised model capability'}
            except (httpx.HTTPError,ValueError):
                return {'handled':True,'accepted':False,'requested':requested,
                        'error':'Could not verify model capability with Ollama; original settings kept'}
            if updated!=prior:
                save_settings(updated,STATE)
            actual=await status()
            answer={'handled':True,'accepted':True,'action':'set_many',
                    'requested':requested,'saved':{key:actual['settings'][key] for key in requested},
                    'settings':actual['settings'],'metadata':actual['metadata'],
                    'effective':actual['effective'],'effective_source':actual.get('effective_source'),
                    'reload_required':actual['reload_required'],
                    'runtime_available':actual['runtime_available'],
                    'model':actual['model'],'scope':'default','applies':'next_request'}
            if apply_now and actual.get('model_loaded') and actual.get('reload_required'):
                try:
                    from .model_memory import control
                    loaded=await control('load',actual['model'])
                    after=await status()
                    answer['effective']=after['effective']
                    answer['reload_required']=after['reload_required']
                    answer['runtime_verified']=bool(loaded.get('verified') and
                                                   after['effective']==after['settings']['context_tokens'])
                    if not answer['runtime_verified']:
                        answer.update({'accepted':False,'error':'Ollama did not confirm context activation'})
                except Exception as exc:
                    answer.update({'accepted':False,'runtime_verified':False,
                                   'error':'Runtime reload failed: '+str(exc)[:250]})
            return answer
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
            'browser_driver':actual['browser_driver'],'browser_runtime':actual['browser_runtime'],
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
