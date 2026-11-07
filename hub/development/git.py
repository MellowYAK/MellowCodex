"""Bounded Git inspection and non-destructive worktree creation."""
import subprocess
import uuid
from pathlib import Path

def command(root,*args,timeout=30):
    root=Path(root).resolve()
    if not root.is_dir():raise ValueError('Project directory missing')
    result=subprocess.run(['git','-C',str(root),*args],capture_output=True,timeout=timeout,encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if len(result.stdout)>2_000_000 or len(result.stderr)>20000:raise ValueError('Git output exceeded inspection budget')
    return result

def status(root):
    probe=command(root,'rev-parse','--show-toplevel')
    if probe.returncode:return {'repository':False,'unborn':False,'dirty':False,'reason':probe.stderr[:1000]}
    actual=Path(probe.stdout.strip()).resolve()
    if actual!=Path(root).resolve():raise ValueError('Select the repository root explicitly')
    head=command(root,'rev-parse','--verify','HEAD')
    branch=command(root,'symbolic-ref','--quiet','--short','HEAD')
    changes=command(root,'status','--porcelain=v1','-z','--untracked-files=all')
    if changes.returncode:raise ValueError(changes.stderr[:1000])
    return {'repository':True,'root':str(actual),'head':head.stdout.strip() if head.returncode==0 else None,'unborn':head.returncode!=0,'branch':branch.stdout.strip() or None,'dirty':bool(changes.stdout),'changes_porcelain':changes.stdout.split('\0')[:-1]}

def worktree(root,destination_root):
    before=status(root)
    if not before['repository'] or before['unborn']:raise ValueError('No committed Git base exists. Use a manifest candidate; existing work is preserved.')
    if before['dirty']:raise ValueError('Uncommitted work exists. Use a manifest candidate to preserve it; no worktree was created from an outdated HEAD.')
    destination_root=Path(destination_root).resolve();destination_root.mkdir(parents=True,exist_ok=True)
    target=destination_root/uuid.uuid4().hex
    if target.exists():raise ValueError('Candidate target already exists')
    branch='local-agent/'+target.name
    result=command(root,'worktree','add','-b',branch,str(target),before['head'],timeout=60)
    if result.returncode:raise ValueError(result.stderr[:2000])
    after=status(root)
    return {'path':str(target),'branch':branch,'base_head':before['head'],'source_unchanged':before==after,'profile':'git-worktree-not-os-sandbox'}
