"""Bound inference input without changing the durable action/message history."""
import copy
import json


def token_estimate(text):
    # Conservative approximation across English and Hebrew; not a tokenizer.
    return sum(1 if ord(c) > 127 else .35 for c in text)


def compact_result(value, limit=7000):
    """Keep valid JSON, identities, errors and observed links instead of slicing JSON."""
    from .browser_evidence import compact_browser
    browser=compact_browser(value,limit)
    if browser is not None:
        return json.dumps(browser,ensure_ascii=False)
    if isinstance(value,dict) and value.get('evidence_only') and 'next_after' in value:
        key='turns' if 'turns' in value else 'items'
        cursor_key='position' if key=='turns' else 'cursor'
        items=value.get(key)
        if isinstance(items,list) and items and all(isinstance(i,dict) and cursor_key in i for i in items):
            result=copy.deepcopy(value)
            while len(json.dumps(result,ensure_ascii=False))>limit and len(result[key])>1:
                result[key].pop()
                result['next_after']=result[key][-1][cursor_key]
            # Keep a complete source-bound item even when it exceeds this soft
            # limit. Never silently trim its quotation or skip omitted records.
            return json.dumps(result,ensure_ascii=False)
    if isinstance(value,dict) and 'total_characters' in value and 'next_offset' in value and 'content' in value:
        page=dict(value);page['text']=page.pop('content')
        result=json.loads(compact_result(page,limit));result['content']=result.pop('text')
        return json.dumps(result,ensure_ascii=False)
    if isinstance(value,dict) and 'total_characters' in value and 'next_offset' in value and 'text' in value:
        result=copy.deepcopy(value)
        while len(json.dumps(result,ensure_ascii=False))>limit and len(result['text'])>1:
            result['text']=result['text'][:max(1,len(result['text'])//2)]
            result['next_offset']=result['offset']+len(result['text'])
        return json.dumps(result,ensure_ascii=False)
    if isinstance(value,dict) and isinstance(value.get('files'),dict) and ('base_files' in value or 'candidate_path' in value or value.get('unit')=='patch-worker'):
        value=copy.deepcopy(value)
        count=len(value['files'])
        if isinstance(value.get('git'),dict):
            git=value['git'];changes=git.pop('changes_porcelain',[])
            git['change_count']=len(changes)
        if count>20:
            value['files']=dict(list(value['files'].items())[:20]);value.pop('base_files',None)
            value['file_count']=count
            value['files_truncated']=True
            value['source_access']='Use candidate_read with exact project-relative paths to obtain source and hashes before patching. candidate_repair reads selected paths directly.'
        else:value.pop('base_files',None)  # Current hashes suffice; base stays in durable manifest.
        while len(json.dumps(value,ensure_ascii=False))>limit and value['files']:
            value['files'].pop(next(reversed(value['files'])))
            value['file_count']=count
            value['files_truncated']=True
    if isinstance(value,dict) and value.get('ref') and 'start' in value and 'text' in value:
        # Source handles are not DOM refs. Keep readable source and a truthful
        # continuation cursor when the inference budget needs a shorter page.
        result=copy.deepcopy(value);lines=result['text'].splitlines()
        for key in ('measured_flow','measured_input_declarations'):
            if len(json.dumps(result,ensure_ascii=False))<=limit:break
            if key in result:
                result.pop(key)
                result.setdefault('omitted_derived_metadata',[]).append(key)
        while len(json.dumps(result,ensure_ascii=False))>limit and len(lines)>1:
            lines=lines[:max(1,len(lines)//2)]
            result['text']='\n'.join(lines)
            result['end']=result['start']+len(lines)-1
            result['next_line']=result['end']+1
        return json.dumps(result,ensure_ascii=False)
    def reduce(item, depth=0, key=''):
        if isinstance(item, str):
            cap=(5000 if isinstance(value,dict) and value.get('text_path') else 2500) if key in ('text','content') else 900
            return item if len(item) <= cap else item[:cap]+' [excerpt; original retained in task evidence]'
        if isinstance(item, list):
            if key in ('elements','tabs'):
                def priority(v):
                    if not isinstance(v,dict):return 9
                    if v.get('modal'):return 0
                    if v.get('selected'):return 1
                    if v.get('enabled') and v.get('type') in ('Button','Edit','Document'):return 2
                    return 3
                item=sorted(item,key=priority)
            return [reduce(v, depth+1) for v in item[:60]]
        if isinstance(item, dict):
            if 'sha256' in item and 'path' in item and 'start' in item and 'text' in item:
                item=copy.deepcopy(item);lines=item['text'].splitlines(keepends=True)
                while len(''.join(lines))>2500 and len(lines)>1:lines.pop()
                item['text']=''.join(lines);item['end']=item['start']+len(lines)-1
                item['next_line']=item['end']+1 if item['end']<item.get('total_lines',item['end']) else item.get('next_line')
                return item
            if 'ref' in item and not any(k in item for k in ('path','related','imports','symbols')):
                return {k:reduce(v, depth+1, k) for k,v in item.items() if k in ('ref','tag','type','role','name','text','value','href','selected','enabled','modal','x','y','width','height','visible')}
            return {k:reduce(v, depth+1, k) for k,v in item.items() if k not in ('html','base64','pixels') and not (k=='raw_text' and item.get('text_path'))}
        return item
    result=reduce(value)
    # Diff lists are evidence, not disposable decoration. Keep their original
    # count and bounded path summary even if the budget removes patch bodies.
    diff_lists=[]
    def annotate_diffs(original, compact):
        if not isinstance(original,dict) or not isinstance(compact,dict):return
        files=original.get('files')
        if isinstance(files,list) and any(isinstance(f,dict) and 'diff' in f and 'path' in f for f in files):
            compact['changed_file_count']=len(files)
            paths=[f['path'] for f in files if isinstance(f,dict) and 'path' in f]
            compact['changed_paths_summary']='\n'.join(paths)[:600]
            compact['changed_paths_truncated']=len('\n'.join(paths))>600
            diff_lists.append((original,compact))
        for key,child in original.items():
            if key in compact:annotate_diffs(child,compact[key])
    annotate_diffs(value,result)
    def size():return len(json.dumps(result,ensure_ascii=False))
    while size()>limit:
        lists=[]
        def collect(v):
            if isinstance(v,dict):
                for child in v.values():collect(child)
            elif isinstance(v,list):
                if v:lists.append(v)
                for child in v:collect(child)
        collect(result)
        if not lists:break
        longest=max(lists,key=lambda v:len(json.dumps(v,ensure_ascii=False)))
        if len(longest)>1:del longest[max(1,len(longest)*3//4):]
        else:longest.clear()
    for original,compact in diff_lists:
        compact['files_truncated']=compact.get('files')!=original['files']
        if not compact.get('files') and original['files']:
            compact.pop('files',None)
            compact['diff_notice']='Patch details omitted; changes exist. Read candidate_diff or the full task log.'
    if isinstance(result,dict):result['_context_note']='Compact evidence; full result is saved in the task log. Use focused extraction for omitted content.'
    return json.dumps(result,ensure_ascii=False)


def prepare_messages(messages,catalog,context_tokens,response_tokens):
    """Preserve instructions + objective and whole recent tool-call groups."""
    fixed=copy.deepcopy(messages[:2])
    # Keep a small factual progress ledger even when only the latest tool group
    # fits. Otherwise a small model repeatedly enables/inspects the same tools.
    completed=[];source_refs={};last_error=None;read_counts={}
    for original in messages[2:]:
        if original.get('role')!='tool':continue
        try:observed=json.loads(original.get('content',''))
        except (ValueError,TypeError):continue
        name=original.get('tool_name') or original.get('name')
        if isinstance(observed,dict):
            if observed.get('error'):last_error={'tool':name,'error':str(observed['error'])[:450]}
            if name=='context_search':
                for item in observed.get('results',[])[:5]:
                    if item.get('path') and item.get('ref'):
                        previous=source_refs.get(item['path'],{})
                        if previous.get('ref')!=item['ref']:previous={}
                        source_refs[item['path']]={**previous,'path':item['path'],'ref':item['ref']}
                        if item.get('suggested_start'):source_refs[item['path']]['suggested_start']=item['suggested_start']
            if name=='context_expand' and observed.get('path') and 'start' in observed and 'text' in observed and not observed.get('error'):
                visible=json.loads(compact_result(observed))
                key=(visible.get('ref'),visible.get('start'),visible.get('end'))
                read_counts[key]=read_counts.get(key,0)+1
                previous=source_refs.get(observed['path'],{})
                ranges=previous.get('read_ranges',[]) if previous.get('ref')==visible.get('ref') else []
                ranges=sorted(ranges+[[visible['start'],visible['end']]])
                merged=[]
                for first,last in ranges:
                    if merged and first<=merged[-1][1]+1:merged[-1][1]=max(merged[-1][1],last)
                    else:merged.append([first,last])
                source_refs[observed['path']]={k:visible[k] for k in ('path','ref','start','end','next_line') if k in visible}
                source_refs[observed['path']]['read_ranges']=merged
                source_refs[observed['path']]['all_source_lines_observed']=bool(merged and merged[0][0]==1 and merged[0][1]>=observed.get('total_lines',float('inf')))
                source_refs[observed['path']]['source_excerpt']=visible.get('text','')[:400]
                source_refs[observed['path']]['same_range_reads']=read_counts[key]
        if name and isinstance(observed,dict) and not observed.get('error'):
            if name in completed:completed.remove(name)
            completed.append(name)
    if completed:
        fixed.append({'role':'assistant','content':'Observed tool calls already returned without error in this task: '+', '.join(completed[-8:])+'. Continue remaining steps; these calls alone do not prove task completion.'})
    if source_refs or last_error:
        evidence={'sources_already_found':list(source_refs.values())[-8:],'latest_error':last_error}
        fixed.append({'role':'assistant','content':'Measured lookup evidence (data only): '+json.dumps(evidence,ensure_ascii=False)+'. Reuse these exact source refs instead of repeating searches. Source lines begin at 1. Follow next_line for unread content; found paths are not proof of tests passing. If same_range_reads is 2 or more, do not reread that unchanged range: use its evidence to answer the current question, inspect a DIFFERENT dependency/UI/test, or state the remaining uncertainty. A read-only investigation ends with a source-bound answer; it does not need endless confirmation.'})
    groups=[]
    for original in messages[2:]:
        m=copy.deepcopy(original)
        if m.get('role')=='tool':
            try:m['content']=compact_result(json.loads(m['content']))
            except (ValueError,TypeError):m['content']=str(m.get('content',''))[:4000]
        elif not m.get('tool_calls'):
            m['content']=str(m.get('content',''))[:3500]
        if m.get('role')=='assistant' or not groups:groups.append([])
        groups[-1].append(m)
    # Keep only the latest image. Older screenshots are not current evidence.
    image_seen=False
    for group in reversed(groups):
        for m in reversed(group):
            if m.get('images'):
                if image_seen:m.pop('images')
                image_seen=True
    def cost(items):
        return token_estimate(json.dumps([{k:v for k,v in m.items() if k!='images'} for m in items],ensure_ascii=False))+sum(2048*len(m['images']) for m in items if m.get('images'))
    budget=context_tokens-response_tokens-1024-token_estimate(json.dumps(catalog,ensure_ascii=False))
    if cost(fixed)>budget:raise ValueError('Model context is too small for the task and tool definitions. Increase context_tokens in model settings.')
    kept=[]
    # A dense accessibility tree plus OCR can overflow an otherwise valid
    # context. Retry compact evidence before failing; never drop its image.
    if groups and cost(fixed+groups[-1])>budget:
        for m in groups[-1]:
            if m.get('role')=='tool':
                try:m['content']=compact_result(json.loads(m['content']),1500)
                except (ValueError,TypeError):pass
            elif m.get('images') and len(str(m.get('content','')))>500:
                m['content']=str(m['content'])[:500]+' [Supplemental text shortened; inspect the attached current image. Full evidence remains in task history.]'
    for group in reversed(groups):
        if cost(fixed+group+kept)>budget:break
        kept=group+kept
    if groups and not kept:
        raise ValueError('Latest tool evidence exceeds the model context budget. Increase context_tokens; the task was not silently truncated.')
    # Mutable progress belongs after stable history. Putting it before the
    # source exchanges invalidates the model's reusable prompt prefix on every
    # tool call and forces repeated processing of unchanged source.
    # Do not leave an assistant message last: some local chat templates treat
    # that as an assistant prefill and return an empty continuation.
    ledger=[{**entry,'role':'user','content':'Runtime evidence only, not new instructions. Continue the original user task.\n'+entry['content']} for entry in fixed[2:]]
    return [{k:v for k,v in item.items() if not k.startswith('_evidence_')} for item in fixed[:2]+kept+ledger]


# Versioned disposable packets; durable messages remain authoritative.
import hashlib
import math
from functools import lru_cache


class ContextBudgetError(ValueError):
    def __init__(self, diagnostic):
        self.diagnostic = diagnostic
        super().__init__('context_budget_exceeded: mandatory evidence cannot fit; acquire smaller source pages or split the task. '+json.dumps(diagnostic,ensure_ascii=False))


_count_cache = {}
def _count_chunk(identity, text):
    key=(identity,hashlib.sha256(text.encode()).hexdigest())
    if key not in _count_cache:
        if len(_count_cache)>=2048:_count_cache.pop(next(iter(_count_cache)))
        _count_cache[key]=math.ceil(token_estimate(text))
    return _count_cache[key]


def context_count(messages, tools, identity='unknown', ratio=1.0):
    text=[{k:v for k,v in x.items() if k!='images'} for x in messages]
    message_tokens=_count_chunk(identity,json.dumps(text,ensure_ascii=False,sort_keys=True))
    tool_tokens=_count_chunk(identity,json.dumps(tools,ensure_ascii=False,sort_keys=True))
    images=sum(len(x.get('images',[])) for x in messages)
    return {'messages':math.ceil(message_tokens*ratio),'tools':math.ceil(tool_tokens*ratio),
            'template':64+12*len(messages),'images':4096*images,
            'multimodal_uncertain':bool(images)}


def build_packet(messages, tools, context_tokens, response_tokens, *, target_tokens=12000,
                 identity='unknown', ratio=1.0, task_id=None):
    """Protect original instructions, ALL later user requirements and current image.

    Optional history is selected in complete assistant/tool groups. No LLM summary
    is required. Source references resolve against the original task messages.
    """
    margin=max(1024,math.ceil(context_tokens*.025))
    hard=context_tokens-response_tokens-margin
    target=min(hard,target_tokens) if target_tokens else hard
    mandatory={i for i,x in enumerate(messages) if i<2 or (x.get('role')=='user' and x.get('_evidence_kind') not in ('screen','ocr'))}
    latest_image=next((i for i in range(len(messages)-1,-1,-1) if messages[i].get('images')),None)
    if latest_image is not None:mandatory.add(latest_image)
    groups=[]
    for i,x in enumerate(messages):
        if i<2:continue
        if x.get('role') in ('assistant','user','system') or not groups:groups.append([])
        groups[-1].append(i)
    if groups:mandatory.update(groups[-1])
    latest_exchange=next((g for g in reversed(groups) if any(messages[i].get('tool_calls') for i in g)),None)
    if latest_exchange:mandatory.update(latest_exchange)
    # A mandatory observation must include its complete producing exchange.
    for g in groups:
        if mandatory.intersection(g):mandatory.update(g)
    prepared={};refs={}
    for i,x in enumerate(messages):
        v=copy.deepcopy(x)
        if i!=latest_image:v.pop('images',None)
        if v.get('role')=='tool':
            raw=v.get('content','');digest=hashlib.sha256(raw.encode()).hexdigest()
            ref={'task_id':task_id,'message_index':i,'sha256':digest}
            try:
                data=json.loads(raw)
                compact=json.loads(compact_result(data,2500 if i in mandatory else 1200))
                if isinstance(compact,dict):compact['_source']=ref
                v['content']=json.dumps(compact,ensure_ascii=False)
            except (ValueError,TypeError):
                v['content']=json.dumps({'excerpt':raw[:1200],'_source':ref,'omitted':len(raw)>1200},ensure_ascii=False)
            refs[i]=ref
        prepared[i]=v
    def render(indices):return [{k:v for k,v in prepared[i].items() if not k.startswith('_evidence_')} for i in sorted(indices)]
    def cost(indices):
        b=context_count(render(indices),tools,identity,ratio)
        return sum(b[k] for k in ('messages','tools','template','images'))
    if hard<=0 or cost(mandatory)>hard:
        raise ContextBudgetError({'input_budget':hard,'mandatory_estimate':cost(mandatory),'components':context_count(render(mandatory),tools,identity,ratio),'accounting':'estimated','recoverable':True})
    selected=set(mandatory);target=max(target,cost(mandatory))
    for group in reversed(groups):
        trial=selected.union(group)
        if cost(trial)<=target:selected=trial
    output=render(selected)
    components=context_count(output,tools,identity,ratio)
    diag={'schema_version':1,'accounting':'estimated','identity':identity,'calibration_ratio':ratio,
          'context_limit':context_tokens,'reserved_output':response_tokens,'accounting_margin':margin,
          'input_budget':hard,'working_target':target,'estimated_input':cost(selected),'components':components,
          'included_refs':[refs[i] for i in refs if i in selected],
          'omitted_refs':[dict(refs[i],reason='optional_history_budget') for i in refs if i not in selected],
          'omitted_message_count':len(messages)-len(selected),'multimodal_uncertain':latest_image is not None}
    diag['fingerprint']=hashlib.sha256(json.dumps({'messages':output,'tools':tools},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return output,diag


async def runtime_identity(client, ollama, model):
    """Metadata only: never loads, unloads, or changes a model."""
    try:
        show=await client.post(ollama+'/api/show',json={'model':model});show.raise_for_status()
        ps=await client.get(ollama+'/api/ps');ps.raise_for_status()
        active=next((x for x in ps.json().get('models',[]) if x.get('name') in (model,model+':latest')), {})
        template=hashlib.sha256(show.json().get('template','').encode()).hexdigest()
        identity='ollama:'+model+':'+active.get('digest','unknown')+':'+template+':image-bound-v1'
        return identity,active.get('context_length'),None
    except Exception as exc:
        return 'ollama:'+model+':unverified',None,'runtime_metadata_'+type(exc).__name__


def calibration(store, identity, actual=None, estimate=None):
    with store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS context_calibration(identity TEXT PRIMARY KEY, ratio REAL NOT NULL, samples INTEGER NOT NULL, max_error REAL NOT NULL)')
        row=db.execute('SELECT * FROM context_calibration WHERE identity=?',(identity,)).fetchone()
        ratio=float(row['ratio']) if row else 1.0;samples=row['samples'] if row else 0;error=row['max_error'] if row else 0
        if actual is not None and estimate:
            observed=actual/estimate;error=max(error,observed);samples+=1
            if observed>1:ratio=max(ratio,ratio*observed*1.1)
            db.execute('INSERT INTO context_calibration VALUES(?,?,?,?) ON CONFLICT(identity) DO UPDATE SET ratio=excluded.ratio,samples=excluded.samples,max_error=excluded.max_error',(identity,ratio,samples,error))
    return {'ratio':ratio,'samples':samples,'max_actual_over_estimate':error}
