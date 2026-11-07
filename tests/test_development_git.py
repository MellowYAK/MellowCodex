import pytest
from hub.development.git import command,status,worktree

def test_unborn_and_dirty_projects_preserved(tmp_path):
    root=tmp_path/'repo';root.mkdir();assert command(root,'init').returncode==0
    (root/'a.py').write_text('x=1')
    assert status(root)['unborn'] and status(root)['dirty']
    with pytest.raises(ValueError,match='No committed'):worktree(root,tmp_path/'worktrees')
    command(root,'add','a.py')
    assert command(root,'-c','user.name=Fixture','-c','user.email=fixture@example.test','commit','-m','fixture base').returncode==0
    (root/'a.py').write_text('x=2')
    with pytest.raises(ValueError,match='Uncommitted'):worktree(root,tmp_path/'worktrees')
    assert (root/'a.py').read_text()=='x=2'

def test_clean_worktree_is_separate_and_keeps_source_branch(tmp_path):
    root=tmp_path/'repo';root.mkdir();command(root,'init');(root/'a.py').write_text('x=1');command(root,'add','a.py')
    command(root,'-c','user.name=Fixture','-c','user.email=fixture@example.test','commit','-m','fixture base')
    before=status(root);result=worktree(root,tmp_path/'worktrees')
    assert result['source_unchanged'] and status(root)==before
    assert status(result['path'])['head']==before['head']
