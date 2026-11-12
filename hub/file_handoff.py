"""Versioned, task-scoped file handoff references for exact listed entries.

References are identity hints, NOT capabilities or authorization. ToolRunner
resolves to the full path before normal owner-policy and workspace checks.
"""
import hashlib
from pathlib import Path


def snapshot_listing(task, directory, limit=400):
    directory = Path(directory).resolve()
    visible, entries = [], []
    for item in sorted(directory.iterdir())[:limit]:
        if item.is_symlink():
            # Never create an observation handle that could change its target.
            visible.append({'name': item.name, 'directory': item.is_dir()})
            continue
        stat = item.stat()
        resolved = item.resolve()
        identity = (str(task['id']) + '\0' + str(resolved) + '\0' +
                    str(stat.st_mtime_ns) + '\0' + str(stat.st_size) + '\0' +
                    str(stat.st_ino))
        ref = 'f:' + hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]
        entry = {'ref': ref, 'path': str(resolved), 'mtime_ns': stat.st_mtime_ns,
                 'size': stat.st_size, 'inode': stat.st_ino,
                 'directory': item.is_dir()}
        entries.append(entry)
        visible.append({'name': item.name, 'directory': item.is_dir(), 'ref': ref})
    return visible, {'task_id': task['id'], 'entries': entries}


def resolve_listing_ref(task, ref, observation, *, directory=False):
    if not isinstance(observation, dict) or observation.get('task_id') != task['id']:
        raise ValueError('No matching file listing for this task; list the directory again')
    matching = [item for item in observation.get('entries', ()) if item.get('ref') == ref]
    if len(matching) != 1:
        raise ValueError('Unknown or ambiguous file reference; list the directory again')
    entry = matching[0]
    if entry['directory'] != directory:
        raise ValueError('Reference has wrong file/directory kind')
    path = Path(entry['path'])
    if path.is_symlink() or not (path.is_dir() if directory else path.is_file()) or path.resolve() != path:
        raise ValueError('Listed file no longer exists or has changed identity')
    stat = path.stat()
    if (stat.st_mtime_ns, stat.st_size, stat.st_ino) != (
            entry['mtime_ns'], entry['size'], entry['inode']):
        raise ValueError('Stale file reference; list the directory again')
    return str(path)
