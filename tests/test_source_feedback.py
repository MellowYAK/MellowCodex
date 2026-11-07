import hashlib
import pytest
from hub.source_feedback import source_feedback

def test_omitted_source_can_be_read_without_rerunning_and_is_task_scoped():
    from hub.source_feedback import recorded_source
    saved=action('original','x'*10000)
    saved['result']['total_lines']=300
    assert source_feedback([saved],budget=1000)['omitted_count']==1
    result=recorded_source([saved],'original')
    assert result['sources'][0]['text']=='x'*10000
    assert result['sources'][0]['total_lines']==300
    with pytest.raises(ValueError):recorded_source([],'original')

def action(identifier,text,path='a.py',start=1):
    return {'id':identifier,'tool':'context_expand','state':'complete',
            'result':{'path':path,'ref':'fast/file:abc','start':start,'end':start+text.count('\n'), 'text':text}}

def test_source_evidence_survives_later_navigation_and_preserves_exact_bytes():
    text='שם = "test"\nreturn True\n'
    actions=[action('source',text)]+[{'tool':'context_search','state':'complete','result':{'results':[]}}]*12
    packet=source_feedback(actions)
    assert packet['complete_delivery']
    assert packet['sources'][0]['text']==text
    assert packet['sources'][0]['excerpt_sha256']==hashlib.sha256(text.encode()).hexdigest()
    assert packet['sources'][0]['end']==3

def test_budget_omissions_are_explicit_without_fabricating_shortened_ranges():
    packet=source_feedback([action('big','x'*5000),action('small','ok',start=100)],budget=1000)
    assert [s['action_id'] for s in packet['sources']]==['small']
    assert packet['omitted_sources'][0]['action_id']=='big'
    assert 'text' not in packet['omitted_sources'][0]
    assert not packet['complete_delivery']
    assert packet['source_count']==2

def test_errors_excluded_but_different_source_versions_not_deduplicated():
    first=action('one','old');second=action('two','new');failed=action('bad','fake')
    failed['result']['error']='read failed'
    packet=source_feedback([first,second,failed])
    assert {s['action_id'] for s in packet['sources']}=={'one','two'}

def test_read_file_offsets_are_preserved():
    packet=source_feedback([{'id':'read','tool':'read_file','state':'complete','args':{'path':'a.py'},
                             'result':{'text':'partial','offset':200,'next_offset':207}}])
    assert packet['sources'][0]['offset']==200
    assert packet['sources'][0]['next_offset']==207
    assert packet['sources'][0]['start'] is None


def test_fast_reference_preserves_version_hash():
    a=action('fast','x')
    a['result']['ref']='fast/file:'+('a'*64)
    assert source_feedback([a])['sources'][0]['source_sha256']=='a'*64
    a['result']['ref']='unversioned'
    assert source_feedback([a])['sources'][0]['source_sha256'] is None
