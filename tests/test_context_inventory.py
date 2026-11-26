import subprocess
import time
import pytest
from test_project_context import context
from hub.context.inventory import walk


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


def test_git_walk_avoids_os_walk_over_ignored_vendor_tree(tmp_path,monkeypatch):
    root=tmp_path/'source';root.mkdir()
    subprocess.run(['git','init',str(root)],check=True,capture_output=True)
    (root/'.gitignore').write_text('vendor/\n')
    (root/'vendor').mkdir()
    (root/'vendor'/'unwanted.py').write_text('ignored=1\n')
    (root/'needed.py').write_text('needed=1\n')
    def no_walk(*args,**kwargs):
        raise AssertionError('Git-backed inventory must not walk ignored trees')
    monkeypatch.setattr('hub.context.inventory.os.walk',no_walk)
    actual=set(walk(root,{'.git','vendor'},time.monotonic()+10))
    assert 'needed.py' in actual
    assert 'vendor/unwanted.py' not in actual


def test_git_walk_skips_deleted_excluded_and_linked_paths(tmp_path,monkeypatch):
    root=tmp_path/'source';root.mkdir()
    subprocess.run(['git','init',str(root)],check=True,capture_output=True)
    (root/'node_modules').mkdir()
    (root/'node_modules'/'old.py').write_text('bad=1\n')
    (root/'gone.py').write_text('gone=1\n')
    (root/'linked.py').write_text('linked=1\n')
    (root/'good.py').write_text('good=1\n')
    subprocess.run(['git','-C',str(root),'add','-f','node_modules/old.py','gone.py','linked.py','good.py'],check=True,capture_output=True)
    (root/'gone.py').unlink()
    original=type(root).is_symlink
    monkeypatch.setattr(type(root),'is_symlink',lambda p: p.name=='linked.py' or original(p))
    actual=set(walk(root,{'.git','node_modules'},time.monotonic()+10))
    assert 'good.py' in actual
    assert 'gone.py' not in actual
    assert 'node_modules/old.py' not in actual
    assert 'linked.py' not in actual


def test_non_git_walk_still_prunes_excluded_directories(tmp_path):
    root=tmp_path/'source';root.mkdir()
    (root/'node_modules').mkdir()
    (root/'node_modules'/'ignored.py').write_text('ignored=1\n')
    (root/'main.py').write_text('main=1\n')
    actual=set(walk(root,{'node_modules'},time.monotonic()+10))
    assert 'main.py' in actual
    assert 'node_modules/ignored.py' not in actual
