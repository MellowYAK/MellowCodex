"""Manifest candidates for local/unborn repositories. No live source writes.

APC design provenance: project_connection.php/source-history contracts, pinned
in docs/apc-reuse-manifest.json. Python implementation; no PHP code copied.
"""
import hashlib
import json
import os
import uuid
from pathlib import Path
from ..context.service import safe_path, allowed, EXCLUDED

def sha(data):return hashlib.sha256(data).hexdigest()

class Workspaces:
    def __init__(self,root):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)

    def candidate(self,identifier):
        if len(identifier)!=32 or any(c not in '0123456789abcdef' for c in identifier):
            raise ValueError('Invalid candidate identity')
        target=self.root/identifier
        if target.is_symlink() or target.is_junction():raise ValueError('Linked candidate root')
        return target

    def create(self,source):
        source=Path(source).resolve()
        if not source.is_dir() or source==Path(source.anchor):raise ValueError('Choose a project directory')
        if self.root.is_relative_to(source):raise ValueError('Candidate storage must be outside source')
        identifier=uuid.uuid4().hex;target=self.candidate(identifier);target.mkdir()
        files={};total=0
        try:
            for folder,dirs,names in os.walk(source,followlinks=False):
                dirs[:]=[d for d in dirs if d.lower() not in EXCLUDED and not (Path(folder)/d).is_symlink() and not (Path(folder)/d).is_junction()]
                for name in names:
                    rel=(Path(folder)/name).relative_to(source).as_posix()
                    if not allowed(rel):continue
                    origin=safe_path(source,rel)
                    if origin.stat().st_size>1_000_000:raise ValueError('Source file exceeds candidate limit')
                    data=origin.read_bytes();total+=len(data)
                    if total>50_000_000 or len(files)>=15000:raise ValueError('Candidate exceeds source budget')
                    output=target/'source'/rel;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
                    files[rel]=sha(data)
            (target/'source').mkdir(exist_ok=True)
            manifest={'id':identifier,'source':str(source),'files':files,'base_files':dict(files),'state':'prepared','revision':0,'profile':'same-account-workspace-not-os-sandbox'}
            from .git import status
            try:manifest['git']=status(source)
            except (OSError,ValueError) as exc:manifest['git']={'available':False,'reason':str(exc)}
            (target/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
            return manifest
        except Exception:
            (target/'failed.json').write_text('{"state":"failed"}',encoding='utf-8')
            raise

    def inspect(self,identifier):
        target=self.candidate(identifier)
        manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
        if manifest.get('id')!=identifier:raise ValueError('Candidate identity mismatch')
        self.directory(identifier,manifest)
        return manifest

    def directory(self,identifier,manifest):
        name=manifest.get('directory','source')
        if name!='source' and not (name.startswith('revision-') and len(name)==41 and all(c in '0123456789abcdef' for c in name[9:])):
            raise ValueError('Invalid candidate directory')
        path=self.candidate(identifier)/name
        if path.is_symlink() or path.is_junction():raise ValueError('Linked candidate directory')
        if not path.is_dir():raise ValueError('Candidate directory missing')
        return path

    def diff(self,identifier):
        import difflib
        manifest=self.inspect(identifier);current=self.directory(identifier,manifest)
        base=self.candidate(identifier)/'source';results=[];remaining=200000
        for rel in sorted(set(manifest.get('base_files',{}))|set(manifest['files'])):
            original=safe_path(base,rel);updated=safe_path(current,rel)
            old=original.read_bytes() if original.is_file() else b''
            new=updated.read_bytes() if updated.is_file() else b''
            if old==new:continue
            delta=''.join(difflib.unified_diff(old.decode('utf-8').splitlines(True),new.decode('utf-8').splitlines(True),fromfile='base/'+rel,tofile='candidate/'+rel))
            results.append({'path':rel,'base_hash':sha(old) if original.is_file() else None,'candidate_hash':sha(new),'diff':delta[:remaining],'truncated':len(delta)>remaining})
            remaining=max(0,remaining-len(delta))
        return {'candidate_id':identifier,'revision':manifest['revision'],'files':results,'activation':'not_activated'}

    def propose(self,identifier,changes,expected_revision):
        """Build a complete next snapshot; publish only after all preconditions pass.

        Caller must serialize mutations per candidate. This creates a staged
        revision, never changes the live checkout or claims test acceptance.
        """
        import shutil
        target=self.candidate(identifier);manifest=self.inspect(identifier)
        if manifest['revision']!=expected_revision:raise ValueError('Candidate revision conflict')
        if not changes or len(changes)>50:raise ValueError('Expected 1–50 file changes')
        current=self.directory(identifier,manifest);validated={}
        for change in changes:
            rel=change['path'];p=safe_path(current,rel)
            if rel in validated:raise ValueError('Duplicate patch path')
            actual=sha(p.read_bytes()) if p.exists() else None
            if actual!=change['base_hash']:raise ValueError('Source hash conflict: '+rel)
            data=change['content'].encode('utf-8')
            if len(data)>1_000_000:raise ValueError('Patch file too large')
            validated[rel]=data
        directory='revision-'+uuid.uuid4().hex;staged=target/directory
        shutil.copytree(current,staged,symlinks=True)
        for rel,data in validated.items():
            p=safe_path(staged,rel);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        manifest.update(directory=directory,revision=expected_revision+1,state='staged')
        manifest['files'].update({rel:sha(data) for rel,data in validated.items()})
        pending=target/('manifest-'+uuid.uuid4().hex+'.tmp')
        pending.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        os.replace(pending,target/'manifest.json')
        return manifest
