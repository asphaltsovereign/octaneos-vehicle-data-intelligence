"""Explicit migration command only; never imported by server startup."""
import os
from pathlib import Path
import psycopg
url=os.environ['MIGRATION_DATABASE_URL']
with psycopg.connect(url,autocommit=True) as conn:
    for path in sorted((Path(__file__).resolve().parents[1]/'migrations').glob('*.sql')):
        exists=conn.execute("SELECT to_regclass('sentinel.schema_migrations')").fetchone()[0]
        if exists and conn.execute('SELECT 1 FROM sentinel.schema_migrations WHERE version=%s',(path.stem,)).fetchone():
            print('Already applied',path.name);continue
        conn.execute(path.read_text())
        print('Applied',path.name)
