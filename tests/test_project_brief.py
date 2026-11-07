import pytest
from test_context_integration import service
from hub.context.indexing import Indexing
from hub.context.api import dispatch, ContextRequest


@pytest.mark.parametrize('mode',['fast','apc_baseline'])
def test_brief_preserves_original_source_and_selected_index(tmp_path,mode):
    svc,project,_=service(tmp_path)
    root=tmp_path/'project'
    (root/'README.md').write_text('Demo project\nSee a.py for total.\n',encoding='utf-8')
    queue=Indexing(svc);queue.settings(project['id'],False,mode)
    queue.selected(project['id']).refresh(project['id'])
    packet=dispatch(svc,'brief',ContextRequest(project_id=project['id'],query='total'))
    assert packet['opening_sources'][0]['text'].splitlines()==(root/'README.md').read_text(encoding='utf-8').splitlines()
    assert packet['search']['results'][0]['path'] in ('a.py','README.md')
    assert packet['inference_required'] is False
    assert packet['overview']['index']
    (root/'README.md').write_text('Changed after index',encoding='utf-8')
    with pytest.raises(ValueError):
        dispatch(svc,'brief',ContextRequest(project_id=project['id']))
