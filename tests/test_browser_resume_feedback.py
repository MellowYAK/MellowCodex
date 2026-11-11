import ast
from pathlib import Path
from hub.browser_workflow import assess

def test_intermediate_page_does_not_request_another_unchanged_read():
    page={'id':'current','text':'Review setup. Finish setup','elements':[{'ref':'e1','name':'Finish setup','enabled':True}]}
    r=assess(page,{'status':'success','evidence':page['text']})
    assert r['verified'] is False
    assert 'remaining authorized action' in r['next_step']
    assert 'Do not repeat this assessment' in r['next_step']

def test_resume_does_not_discard_review_messages():
    source=(Path(__file__).parents[1]/'hub/engine.py').read_text(encoding='utf-8')
    tree=ast.parse(source)
    matches=[n for n in ast.walk(tree) if isinstance(n,ast.Assign) and 'Resuming the SAME incomplete objective' in ast.get_source_segment(source,n)]
    assert len(matches)==1
    assert isinstance(matches[0].value,ast.BinOp)
    assert isinstance(matches[0].value.left,ast.Name) and matches[0].value.left.id=='messages'

def test_resume_refresh_is_read_only_and_consumed():
    source=(Path(__file__).parents[1]/'hub/engine.py').read_text(encoding='utf-8')
    assert "not (name=='browser_observe' and resume_observation_pending)" in source
    assert "if name=='browser_observe':resume_observation_pending=False" in source
    assert 'resume_observation_pending=bool(prior)' in source
