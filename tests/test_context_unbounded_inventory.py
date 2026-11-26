"""Regressions: source index permits large Git projects and modern JS module files."""
from pathlib import Path
from types import SimpleNamespace

from hub.context.fast import FastContext
from hub.context.inventory import git_paths, walk
from hub.context.service import MAX_FILES, allowed
from test_project_context import context


def test_extended_source_extensions_are_indexable_and_protected():
    assert MAX_FILES is None
    for name in ('src/v3/direct/native-worker.mjs', 'tasks/worker.cjs',
                 'src/app.mts', 'src/app.cts', 'ui/view.vue',
                 'ui/view.svelte', 'src/module.rs', 'src/module.go',
                 'scripts/bootstrap.ps1'):
        assert allowed(name), name
        assert FastContext.allowed(name), name
    assert FastContext.role('src/v3/direct/native-worker.mjs') == 'source'
    assert FastContext.allowed('scripts/deploy.sh')
    assert not allowed('scripts/deploy.sh')  # Preserve baseline mode compatibility.
    assert not allowed('node_modules/foo.mjs')
    assert not allowed('secrets/private.mjs')
    assert not allowed('.env.mjs')


def test_git_list_not_rejected_after_four_megabytes(tmp_path, monkeypatch):
    root = tmp_path / 'source'
    root.mkdir()
    (root / '.git').mkdir()
    payload = b'only-one-file.py\x00' * 300000
    assert len(payload) > 4_000_000
    def fake_run(command, stdout, stderr, **kwargs):
        assert kwargs['timeout'] >= 60
        stdout.write(payload)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr('hub.context.inventory.subprocess.run', fake_run)
    assert git_paths(root) == {'only-one-file.py'}


def test_git_inventory_has_no_hundred_thousand_file_ceiling(tmp_path, monkeypatch):
    root = tmp_path / 'source'
    root.mkdir()
    names = ('f' + str(i) + '.py' for i in range(100001))
    monkeypatch.setattr('hub.context.inventory.git_paths', lambda _: names)
    monkeypatch.setattr(Path, 'is_symlink', lambda self: False)
    monkeypatch.setattr(Path, 'is_junction', lambda self: False)
    monkeypatch.setattr(Path, 'is_file', lambda self: True)
    import hub.context.inventory as inventory
    def no_os_walk(*args, **kwargs):
        raise AssertionError('Git inventory should bypass filesystem traversal')
    monkeypatch.setattr(inventory.os, 'walk', no_os_walk)
    assert sum(1 for _ in walk(root, {'.git'}, None)) == 100001


def test_mjs_source_content_is_searchable(context):
    svc, project, root = context
    (root / 'native-worker.mjs').write_text(
        'const verifiedMjsFunctionForIndex = () => 47;\n', encoding='utf-8')
    result = svc.refresh(project)
    assert result['indexed'] >= 1
    assert any(row['path'] == 'native-worker.mjs'
               for row in svc.search(project, 'verifiedMjsFunctionForIndex')['results'])
