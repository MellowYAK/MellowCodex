"""Bounded Git-aware inventory; read failures abort deletion reconciliation."""
import os
import subprocess
import tempfile
import time
from pathlib import Path


def git_paths(root):
    if not (root/'.git').exists():return None
    with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as errors:
        result=subprocess.run(['git','-C',str(root),'ls-files','-z','--cached','--others','--exclude-standard'],stdout=output,stderr=errors,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise OSError('Git inventory failed; previous index preserved')
        if output.tell()>4_000_000:raise ValueError('Git inventory exceeded 4 MB budget')
        output.seek(0)
        return set(output.read().decode('utf-8').split('\0'))-{''}


def walk(root,excluded,deadline):
    tracked=git_paths(root);visited=0
    def failed(error):raise error
    for folder,dirs,names in os.walk(root,followlinks=False,onerror=failed):
        visited+=len(dirs)+len(names)
        if visited>100_000 or time.monotonic()>deadline:raise ValueError('Index traversal budget exceeded; previous index preserved')
        dirs[:]=[d for d in dirs if d.lower() not in excluded and not (Path(folder)/d).is_symlink() and not (Path(folder)/d).is_junction()]
        for name in names:
            rel=(Path(folder)/name).relative_to(root).as_posix()
            if tracked is None or rel in tracked:yield rel
