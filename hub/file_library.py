"""Durable local files shared by chat uploads, browser downloads and agent tools."""
from contextlib import contextmanager
import hashlib
import mimetypes
import re
import sqlite3
import time
import uuid
from pathlib import Path
from .config import STATE, ROOT

MAX_UPLOAD = 100 * 1024 * 1024


def safe_name(name):
    name = re.split(r'[/\\]', str(name))[-1]
    name = re.sub(r'[\x00-\x1f<>:"/\\|?*]', '_', name).strip(' .')[:180]
    if not name or name.split('.')[0].upper() in {'CON','PRN','AUX','NUL', *(f'COM{i}' for i in range(10)), *(f'LPT{i}' for i in range(10))}:
        name = 'file-' + name
    return name


class FileLibrary:
    def __init__(self, state=None, root=None):
        self.state = Path(state or STATE)
        self.root = Path(root or (ROOT / 'files')).resolve()
        self.state.mkdir(parents=True, exist_ok=True)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.state / 'files.sqlite3'
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY, name TEXT, path TEXT, mime TEXT, source TEXT,
                status TEXT, size INTEGER DEFAULT 0, sha256 TEXT DEFAULT '',
                created REAL, error TEXT DEFAULT '')''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:yield db
        finally:db.close()

    def reserve(self, name, source, mime=''):
        ident = uuid.uuid4().hex
        name = safe_name(name)
        path = self.root / ident / name
        path.parent.mkdir()
        with self.connect() as db:
            db.execute('INSERT INTO files(id,name,path,mime,source,status,created) VALUES(?,?,?,?,?,?,?)',
                       (ident,name,str(path),mime or mimetypes.guess_type(name)[0] or 'application/octet-stream',source,'receiving',time.time()))
        return self.get(ident)

    def get(self, ident, ready=False):
        with self.connect() as db:
            row = db.execute('SELECT * FROM files WHERE id=?',(ident,)).fetchone()
        if not row: raise KeyError('File not found')
        result = dict(row)
        path = Path(result['path']).resolve()
        if not path.is_relative_to(self.root): raise ValueError('File outside library')
        if ready and (result['status'] != 'ready' or not path.is_file()):
            raise ValueError('File is not downloaded completely or has been moved')
        return result

    def finish(self, ident):
        item = self.get(ident)
        path = Path(item['path'])
        with path.open('rb') as file:
            digest = hashlib.file_digest(file, 'sha256').hexdigest()
        with self.connect() as db:
            db.execute("UPDATE files SET status='ready',size=?,sha256=?,error='' WHERE id=?",(path.stat().st_size,digest,ident))
        return self.get(ident, ready=True)

    def fail(self, ident, reason):
        with self.connect() as db:
            db.execute("UPDATE files SET status='failed',error=? WHERE id=?",(str(reason)[:500],ident))

    def list(self, limit=100):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM files ORDER BY created DESC LIMIT ?', (max(1,min(500,limit)),))]

    def import_bytes(self, name, raw, mime='', source='chat upload'):
        if len(raw)>MAX_UPLOAD: raise ValueError('File exceeds 100 MB')
        item=self.reserve(name,source,mime)
        try:
            Path(item['path']).write_bytes(raw)
            return self.finish(item['id'])
        except Exception as exc:
            self.fail(item['id'],str(exc));raise
