"""One-command local demonstration launcher. Persists records under tools/.local-postgres."""
import os,subprocess,sys,socket,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
env={**os.environ,'OCTANE_ENV':'development','OCTANE_DEMO':'1','OCTANE_DATABASE_ENGINE':'pglite','DATABASE_URL':'postgresql://postgres@127.0.0.1:55432/postgres?sslmode=disable','PGLITE_PORT':'55432','PGLITE_DATA_DIR':str(root/'tools/.local-postgres')}
env['MIGRATION_DATABASE_URL']=env['DATABASE_URL']
# This local release deliberately has no cloud AI integration or external AI calls.
env['OCTANE_AI_PROVIDER']='none'
pg=subprocess.Popen(['node','local-postgres.mjs'],cwd=root/'tools',env=env)
try:
    for _ in range(300):
        if pg.poll() is not None:raise RuntimeError('Database did not start; inspect the message above.')
        try:
            with socket.create_connection(('127.0.0.1',55432),timeout=.2):break
        except OSError:time.sleep(.1)
    else:raise RuntimeError('Database startup timed out.')
    subprocess.run([sys.executable,'backend/scripts/migrate.py'],cwd=root,env=env,check=True)
    print('\nOpen http://127.0.0.1:8000 and choose Enter demonstration workshop.\nDEMO ONLY: use synthetic records. Ctrl+C stops both services.\n',flush=True)
    subprocess.run([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],cwd=root/'backend',env=env,check=True)
except KeyboardInterrupt:pass
finally:
    pg.terminate()
    try:pg.wait(timeout=10)
    except subprocess.TimeoutExpired:pg.kill();pg.wait()
