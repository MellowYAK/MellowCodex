import copy
import json
import pytest
from hub.model_context import prepare_messages, compact_result


@pytest.mark.parametrize('key,cursor_key,cursors', [('items','cursor',[40,39,38,37]),('turns','position',[1,2,3,4])])
def test_conversation_page_compaction_does_not_skip_unseen_records(key,cursor_key,cursors):
    page={key:[{cursor_key:n,'quote':'source '+str(n)+'x'*300} for n in cursors],
          'next_after':cursors[-1],'evidence_only':True}
    original=copy.deepcopy(page)
    result=json.loads(compact_result(page,600))
    assert 0<len(result[key])<len(page[key])
    assert result['next_after']==result[key][-1][cursor_key]
    assert result[key]==page[key][:len(result[key])]
    assert page==original


def test_last_conversation_page_regains_cursor_when_compacted():
    page={'items':[{'cursor':n,'quote':'x'*200} for n in [3,2,1]],'next_after':None,'evidence_only':True}
    result=json.loads(compact_result(page,350))
    assert result['next_after']==3
    assert result['items'][0]['quote']=='x'*200

def test_source_handles_keep_content_relationships_and_continuation():
    source={'ref':'id:hash','path':'src.py','start':1,'end':100,'total_lines':100,'next_line':None,'text':'\n'.join('important code '+str(i) for i in range(100))}
    data=json.loads(compact_result(source,600))
    assert data['text'].startswith('important code') and data['path']=='src.py'
    assert data['next_line']==data['end']+1 and data['end']<100
    related={'ref':'id:hash','imports':['module'],'related':[{'ref':'test:hash','path':'test_src.py','kind':'tested_by'}]}
    assert json.loads(compact_result(related))['related'][0]['path']=='test_src.py'
    result={'results':[{'ref':'id:hash','path':'src.py','excerpt':'needle','hash':'hash'}]}
    assert json.loads(compact_result(result))['results'][0]['excerpt']=='needle'


def test_large_observations_keep_goal_and_valid_refs_without_mutating_audit():
    observation={'id':'fresh','url':'https://example.test/', 'text':'תוכן '*10000,
                 'elements':[{'ref':str(i),'name':'Article '+str(i),'href':'https://example.test/'+str(i),'x':i,'width':100} for i in range(200)]}
    messages=[{'role':'system','content':'Use tools.'},{'role':'user','content':'Save the requested article as PDF.'}]
    for i in range(10):
        messages += [{'role':'assistant','tool_calls':[{'function':{'name':'browser_observe','arguments':{}}}]},
                     {'role':'tool','tool_name':'browser_observe','content':json.dumps(observation)},
                     {'role':'user','content':'Visual evidence','images':['image'+str(i)]}]
    original=copy.deepcopy(messages)
    result=prepare_messages(messages,[],8192,512)
    assert result[:2]==messages[:2] and messages==original
    assert len(result)<len(messages)
    assert [m['images'] for m in result if m.get('images')]==[['image9']]
    data=json.loads(next(m['content'] for m in reversed(result) if m['role']=='tool'))
    assert data['id']=='fresh' and data['elements'][0]['href']=='https://example.test/0'
    for i,m in enumerate(result):
        if m['role']=='tool':assert result[i-1].get('tool_calls')


def test_small_context_fails_explicitly_instead_of_dropping_user_objective():
    with pytest.raises(ValueError,match='too small'):
        prepare_messages([{'role':'system','content':'x'*20000},{'role':'user','content':'goal'}],[],2048,512)


def test_compaction_keeps_file_identity_and_failure():
    data={'id':'file-id','path':'E:/workspace/report.pdf','error':'Upload failed','rows':list(range(10000))}
    compact=json.loads(compact_result(data,1000))
    assert compact['id']==data['id'] and compact['path']==data['path'] and compact['error']==data['error']
    assert len(compact['rows'])<len(data['rows'])


def test_nested_repair_diff_never_reports_empty_changes_when_omitted():
    original={'candidate_id':'c','diff':{'files':[
        {'path':'hub/bridge.py','diff':'x'*10000,'base_hash':'a'*64,'candidate_hash':'b'*64},
        {'path':'tests/test_bridge.py','diff':'y'*10000}]},'output':'z'*900}
    before=copy.deepcopy(original)
    result=json.loads(compact_result(original,1500))['diff']
    assert result['changed_file_count']==2
    assert 'hub/bridge.py' in result['changed_paths_summary']
    assert result['files_truncated'] is True
    assert result.get('files')!=[]
    assert original==before

def test_ocr_text_keeps_later_paragraphs_and_evidence_path():
    text='א'*1100+' subsequent paragraph '+ 'ב'*1200
    data=json.loads(compact_result({'text':text,'text_path':'E:/task/ocr.txt'}))
    assert data['text']==text and data['text_path']=='E:/task/ocr.txt'

def test_active_last_tab_survives_dense_observation_compaction():
    tabs=[{'title':'old '+str(i),'selected':False} for i in range(100)]
    tabs.append({'title':'current document','selected':True})
    data=json.loads(compact_result({'selected_tab':'current document','tabs':tabs},500))
    assert data['selected_tab']=='current document'
    assert data['tabs'][0]['selected'] is True


def test_progress_ledger_survives_recent_group_compaction():
    messages=[{'role':'system','content':'Use tools.'},{'role':'user','content':'Read the candidate.'}]
    for name,result in [('tools_enable',{'enabled_groups':['development']}),('failed_tool',{'error':'denied'}),('candidate_inspect',{'id':'c','revision':0})]:
        messages.extend([{'role':'assistant','tool_calls':[{'function':{'name':name,'arguments':{}}}]},{'role':'tool','tool_name':name,'content':json.dumps(result)}])
    result=prepare_messages(messages,[],4096,512)
    assert result[:2]==messages[:2]
    ledger=next(m['content'] for m in result if 'Observed tool calls' in m.get('content',''))
    assert 'tools_enable' in ledger and 'candidate_inspect' in ledger
    assert 'failed_tool' not in ledger


def test_lookup_refs_and_schema_error_survive_compaction():
    messages=[{'role':'system','content':'Use tools'},{'role':'user','content':'Run tests'}]
    for name,result in [('context_search',{'results':[{'path':'tests/test_real.py','ref':'real:hash'}]}),('context_expand',{'error':'start must be at least 1'})]:
        messages += [{'role':'assistant','tool_calls':[{'function':{'name':name,'arguments':{}}}]},{'role':'tool','tool_name':name,'content':json.dumps(result)}]
    result=prepare_messages(messages,[],4096,512)
    packet=next(m['content'] for m in result if 'Measured lookup' in m.get('content',''))
    assert 'real:hash' in packet and 'tests/test_real.py' in packet
    assert 'start must be at least 1' in packet
    assert messages[0]['content']=='Use tools'


def test_search_does_not_erase_already_read_source_evidence():
    messages=[{'role':'system','content':'Use tools'},{'role':'user','content':'Inspect source'}]
    for name,data in [('context_expand',{'path':'a.py','ref':'a:hash','start':1,'end':1,'text':'return 42','next_line':None}),
                      ('context_search',{'results':[{'path':'a.py','ref':'a:hash','suggested_start':1}]})]:
        messages.extend([{'role':'assistant','tool_calls':[{'function':{'name':name,'arguments':{}}}]},
                         {'role':'tool','tool_name':name,'content':json.dumps(data)}])
    packet=next(m['content'] for m in prepare_messages(messages,[],4096,512) if 'Measured lookup' in m.get('content',''))
    assert 'return 42' in packet and 'same_range_reads' in packet


def test_read_range_ledger_unions_pages_and_resets_changed_hash():
    messages=[{'role':'system','content':'Use tools'},{'role':'user','content':'Inspect source'}]
    for start,end,ref in [(1,2,'a:old'),(3,4,'a:old')]:
        data={'path':'a.py','ref':ref,'start':start,'end':end,'text':'a\nb','next_line':end+1 if end<4 else None,'total_lines':4}
        messages.extend([{'role':'assistant','tool_calls':[{'function':{'name':'context_expand','arguments':{}}}]},
                         {'role':'tool','tool_name':'context_expand','content':json.dumps(data)}])
    def packet():return next(m['content'] for m in prepare_messages(messages,[],4096,512) if 'Measured lookup' in m.get('content',''))
    assert '"read_ranges": [[1, 4]]' in packet() and '"all_source_lines_observed": true' in packet()
    data.update(ref='a:new',start=3,end=4)
    messages.extend([{'role':'assistant','tool_calls':[{'function':{'name':'context_expand','arguments':{}}}]},
                     {'role':'tool','tool_name':'context_expand','content':json.dumps(data)}])
    assert '"read_ranges": [[3, 4]]' in packet() and '"all_source_lines_observed": false' in packet()


def test_mutable_ledger_does_not_precede_stable_source_history():
    messages=[{'role':'system','content':'Use tools'},{'role':'user','content':'Inspect source'},
              {'role':'assistant','tool_calls':[{'function':{'name':'context_expand','arguments':{'ref':'a:h'}}}]},
              {'role':'tool','tool_name':'context_expand','content':json.dumps({'path':'a.py','ref':'a:h','start':1,'end':1,'text':'def observed(): pass','total_lines':1,'next_line':None})}]
    result=prepare_messages(messages,[],8192,512)
    assert result[2]==messages[2] and result[3]['role']=='tool'
    assert result[-1]['role']=='user' and 'Measured lookup evidence' in result[-1]['content']
def test_source_compaction_discards_derived_flow_before_original_lines():
    import json
    from hub.model_context import compact_result
    source={'ref':'fast/a:hash','path':'a.py','start':1,'end':2,'total_lines':2,'text':'first\nsecond',
            'measured_flow':{'facts':['huge'*5000]},'measured_input_declarations':[{'field':'value'}]}
    result=json.loads(compact_result(source,limit=1000))
    assert result['text']=='first\nsecond' and result['end']==2
    assert result['omitted_derived_metadata']==['measured_flow']
    assert result['measured_input_declarations']==source['measured_input_declarations']
    assert 'measured_flow' in source
