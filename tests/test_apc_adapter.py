import json
from test_project_context import context


def test_typed_apc_entity_hash_is_not_file_hash(context):
    svc,p,root=context
    (root/'a.py').write_text('value=1')
    svc.refresh(p)
    docs={'documents':[
        {'doc_id':'file:1','entity_type':'file','entity_id':'a','path_or_route':'a.py','source_hash':'entity-digest','raw_terms':['alpha','beta']},
        {'doc_id':'route:1','entity_type':'route','path_or_route':'/login','raw_terms':['login']},
        {'doc_id':'file:2','entity_type':'file','path_or_route':'a.py','content_hash':'0'*64},
        {'doc_id':'file:1','entity_type':'file','path_or_route':'a.py','aliases':['conflicting']}]}
    (root/'apc.json').write_text(json.dumps(docs))
    result=svc.import_apc(p,'apc.json')
    assert result['imported']==1 and result['skipped']==3
    assert result['documents'][0]['file_hash_verified'] is False
    assert result['documents'][0]['entity_hash']=='entity-digest'
    assert 'Unsupported entity' in result['documents'][1]['reason']
    assert 'Stale' in result['documents'][2]['reason']
    assert 'Duplicate' in result['documents'][3]['reason']
    assert svc.annotations(p,'a.py')[0]['payload']['notes']=='alpha\nbeta'
    assert svc.import_apc(p,'apc.json')['imported']==1
    assert svc.annotations(p,'a.py')[0]['revision']==1
