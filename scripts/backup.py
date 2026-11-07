"""Consistent SQLite backup; never copy a live WAL database as a lone file."""
import sqlite3
from datetime import datetime
from pathlib import Path
root=Path('E:/AI')
destination=root/'backups'/('hub-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.sqlite3')
with sqlite3.connect(root/'state/hub.sqlite3') as source, sqlite3.connect(destination) as target:
    source.backup(target)
print(destination)
