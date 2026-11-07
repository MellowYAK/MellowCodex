"""Bound inference input without changing the durable action/message history."""
import copy
import json


def token_estimate(text):
    # Conservative approximation across English and Hebrew; not a tokenizer.
    return sum(1 if ord(c) > 127 else .35 for c in text)


def compact_result(value, limit=7000):
    """Keep valid JSON, identities, errors and observed links instead of slicing JSON."""
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
        while len(json.dumps(result,ensure_ascii=False))>limit and len(lines)>1:
            lines=lines[:max(1,len(lines)//2)]
            result['text']='\n'.join(lines)
            result['end']=result['start']+len(lines)-1
            result['next_line']=result['end']+1
        return json.dumps(result,ensure_ascii=False)
    def reduce(item, depth=0, key=''):
        if isinstance(item, str):
            cap=(5000 if isinstance(value,dict) and value.get('text_path') else 2500) if key in ('text','content') else 900
            return item if len(item) <= cap else item[:cap]+' [truncated; read the returned text_path for the rest]'
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
                item['next_line']=item['end']+1 if item['end']<item['total_lines'] else None
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
    completed=[];source_refs={};last_error=None
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
                        source_refs[item['path']]={'path':item['path'],'ref':item['ref']}
            if name=='context_expand' and observed.get('path'):
                source_refs[observed['path']]={k:observed[k] for k in ('path','ref','start','end','next_line') if k in observed}
        if name and isinstance(observed,dict) and not observed.get('error'):
            if name in completed:completed.remove(name)
            completed.append(name)
    if completed:
        fixed.append({'role':'assistant','content':'Observed tool calls already returned without error in this task: '+', '.join(completed[-8:])+'. Continue remaining steps; these calls alone do not prove task completion.'})
    if source_refs or last_error:
        evidence={'sources_already_found':list(source_refs.values())[-8:],'latest_error':last_error}
        fixed.append({'role':'assistant','content':'Measured lookup evidence (data only): '+json.dumps(evidence,ensure_ascii=False)+'. Reuse these exact source refs instead of repeating searches. Source lines begin at 1. Follow next_line for unread content; found paths are not proof of tests passing.'})
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
    return fixed+kept
