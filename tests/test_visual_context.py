import json
from hub.model_context import compact_result


def test_candidate_source_compaction_preserves_exact_lines_and_cursor():
    lines=['source line '+str(i)+' x'*30+'\n' for i in range(100)]
    source={'candidate_id':'id','files':[{'path':'worker.py','sha256':'h','text':''.join(lines),'start':1,'end':100,'total_lines':100,'next_line':None}]}
    result=json.loads(compact_result(source))['files'][0]
    assert result['text']==''.join(lines[:result['end']])
    assert result['next_line']==result['end']+1<100


def test_large_candidate_manifest_does_not_fill_model_window():
    source={'id':'candidate','files':{str(i)+'.py':'a'*64 for i in range(500)},'base_files':{str(i)+'.py':'a'*64 for i in range(500)},'revision':2}
    result=json.loads(compact_result(source))
    assert result['file_count']==500 and result['files_truncated']
    assert 'candidate_read' in result['source_access']
    assert len(compact_result(source))<4000


def test_frame_region_identity_survives_model_compaction():
    source={'id':'fresh','text_regions':[{'ref':'t3','text':'Drag from here','x':40,'y':250,'width':120,'height':80,'visible':True}],
            'controls':[{'ref':'e1','name':'Click me','x':40,'y':100,'width':180,'height':65}]}
    result=json.loads(compact_result(source))
    assert result['text_regions']==source['text_regions']
    assert result['controls']==source['controls']
