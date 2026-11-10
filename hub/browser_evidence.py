"""Compact actionable browser evidence without guessing targets."""
import json
from .errors import ObservationError

def resolve_ref(observation, reference):
    if reference in observation['refs']:
        return reference
    # A small model may copy the observed accessible name into ref. Accept
    # only a unique exact name from THIS observation, never a DOM search.
    matches=[e['ref'] for e in observation.get('elements', [])
             if e.get('name') and e['name']==reference]
    if len(matches)==1:
        return matches[0]
    if len(matches)>1:
        raise ObservationError('Ambiguous observed name. Use the exact element ref.')
    raise ObservationError('Unknown element reference. Use a ref from the latest elements, or browser_observe with query.')

def compact_browser(value, limit):
    if not isinstance(value,dict):
        return None
    if isinstance(value.get('after'),dict):
        after=compact_browser(value['after'],max(900,limit-500))
        if after is not None:
            return {**{k:v for k,v in value.items() if k!='after'},'after':after}
    if not value.get('id') or not isinstance(value.get('elements'),list):
        return None
    out={k:value[k] for k in ('id','url','title','path','screenshot_available','observation_source','query','query_matched','query_note','element_count') if k in value}
    out['notices']=value.get('notices',[])
    out['elements']=[]
    out['element_count']=value.get('element_count',len(value['elements']))
    out['action_hint']='Use id as observation_id and an elements.ref as ref. Use browser_observe(query=...) for omitted controls. Never guess refs.'
    # Controls take priority over body prose, navigation links and geometry.
    for e in value['elements']:
        row={k:e[k] for k in ('ref','tag','type','role','name','value','href','enabled','options','options_truncated') if k in e}
        if len(json.dumps({**out,'elements':out['elements']+[row]},ensure_ascii=False))>limit-350:
            break
        out['elements'].append(row)
    out['elements_omitted']=len(value['elements'])-len(out['elements'])
    available=max(0,limit-100-len(json.dumps(out,ensure_ascii=False)))
    out['text']=str(value.get('text',''))[:min(1200,available)]
    out['text_truncated']=len(str(value.get('text','')))>len(out['text'])
    return out

def filter_controls(state,query):
    state['element_count']=len(state['elements'])
    if not query:return state
    if len(query)>200:raise ValueError('Browser query must be at most 200 characters')
    matched=[e for e in state['elements'] if query.casefold() in str(e.get('name','')).casefold()]
    state['query']=query
    state['query_matched']=bool(matched)
    if matched:state['elements']=matched
    else:state['query_note']='No literal match. Returned current controls unfiltered. Read their actual visible language and choose an observed ref; do not repeat the same unmatched query.'
    return state
