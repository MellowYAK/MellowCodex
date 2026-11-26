"""Bounded Git-aware inventory; read failures abort deletion reconciliation."""
import os
import subprocess
import tempfile
import time
from pathlib import Path


def git_paths(root):
    if not (root/'.git').exists():return None
    with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as errors:
        result=subprocess.run(['git','-C',str(root),'ls-files','-z','--cached','--others','--exclude-standard'],stdout=output,stderr=errors,timeout=600,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise OSError('Git inventory failed; previous index preserved')
        output.seek(0)
        return set(output.read().decode('utf-8').split('\0'))-{''}


def walk(root,excluded,deadline):
    tracked=git_paths(root)
    def failed(error):raise error
    if tracked is not None:
        # Git already excludes ignored vendor directories. Enumerate that
        # bounded inventory directly instead of walking the entire filesystem.
        for rel in sorted(tracked):
            if deadline is not None and time.monotonic()>deadline:raise ValueError('Index traversal deadline exceeded; previous index preserved')
            path=Path(rel)
            if not path.parts or path.is_absolute() or '..' in path.parts or ':' in rel:
                continue
            if any(part.lower() in excluded for part in path.parts[:-1]):
                continue
            current=Path(root);linked=False
            for part in path.parts:
                current=current/part
                if current.is_symlink() or current.is_junction():
                    linked=True;break
            if not linked and current.is_file():
                yield path.as_posix()
        return
    for folder,dirs,names in os.walk(root,followlinks=False,onerror=failed):
        dirs[:]=[d for d in dirs if d.lower() not in excluded and not (Path(folder)/d).is_symlink() and not (Path(folder)/d).is_junction()]
        if deadline is not None and time.monotonic()>deadline:raise ValueError('Index traversal deadline exceeded; previous index preserved')
        for name in names:
            yield (Path(folder)/name).relative_to(root).as_posix()
