"""Fail-fast Windows writer ownership, released by the OS on process exit."""
from contextlib import contextmanager
from pathlib import Path
import msvcrt


@contextmanager
def candidate_owner(directory,label='Candidate'):
    path=Path(directory)/'writer.lock'
    if path.is_symlink() or path.is_junction():raise ValueError('Linked writer lock')
    with path.open('a+b') as handle:
        if handle.tell()==0:handle.write(b'0');handle.flush()
        handle.seek(0)
        try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        except OSError as exc:raise ValueError(label+' is busy in another operation; inspect current status before retrying') from exc
        try:yield
        finally:
            handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
