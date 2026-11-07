import subprocess
import pytest
from test_project_context import context


def test_git_ignored_sources_are_not_indexed(context):
    svc,p,root=context
    subprocess.run(['git','init',str(root)],check=True,capture_output=True)
    (root/'.gitignore').write_text('ignored/\n')
    (root/'ignored').mkdir();(root/'ignored'/'private.py').write_text('hidden_marker=1')
    (root/'visible.py').write_text('visible_marker=1')
    svc.refresh(p)
    assert svc.search(p,'visible_marker')['results']
    assert not svc.search(p,'hidden_marker')['results']


def test_failed_inventory_preserves_previous_snapshot(context,monkeypatch):
    svc,p,root=context
    (root/'a.py').write_text('old_marker=1');svc.refresh(p)
    before=svc.overview(p)['index']['revision']
    (root/'a.py').write_text('new_marker=1')
    def fail(*args):
        yield 'a.py'
        raise PermissionError('directory inaccessible')
    monkeypatch.setattr('hub.context.inventory.walk',fail)
    with pytest.raises(PermissionError):svc.refresh(p)
    assert svc.overview(p)['index']['revision']==before
    assert svc.search(p,'old_marker')['results']
    assert not svc.search(p,'new_marker')['results']
