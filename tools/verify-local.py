"""Start disposable PostgreSQL/WASM and execute checks in one process environment."""
import os,subprocess,sys,time,socket,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
python=root/'.venv/bin/python'
if not python.exists():python=Path(sys.executable)
env={**os.environ,'OCTANE_ENV':'development','OCTANE_DEMO':'1','OCTANE_DATABASE_ENGINE':'pglite','DATABASE_URL':'postgresql://postgres@127.0.0.1:55432/postgres?sslmode=disable','PGLITE_DATA_DIR':tempfile.mkdtemp(prefix='octane-test-db-'),'PGLITE_PORT':'55432'}
env['TEST_DATABASE_URL']=env['MIGRATION_DATABASE_URL']=env['DATABASE_URL']
pg=subprocess.Popen(['node','local-postgres.mjs'],cwd=root/'tools',env=env,stdout=subprocess.DEVNULL)
server=None
try:
    for _ in range(200):
        try:
            with socket.create_connection(('127.0.0.1',55432),timeout=.2):break
        except OSError:
            if pg.poll() is not None:raise RuntimeError('Local database exited')
            time.sleep(.1)
    else:raise RuntimeError('Database did not start')
    subprocess.run([str(python),'backend/scripts/migrate.py'],cwd=root,env=env,check=True)
    if '--browser' in sys.argv:
        server=subprocess.Popen([str(python),'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],cwd=root/'backend',env=env,stdout=subprocess.DEVNULL)
        for _ in range(100):
            try:
                with socket.create_connection(('127.0.0.1',8000),timeout=.2):break
            except OSError:time.sleep(.1)
        subprocess.run(['node','browser-workflow.cjs'],cwd=root/'tools',env=env,check=True)
    else:
        tests=[a for a in sys.argv[1:] if not a.startswith('--')]
        subprocess.run([str(python),'-m','pytest','-q',*(tests or ['tests'])],cwd=root/'backend',env=env,check=True)
finally:
    if server:
        server.terminate();server.wait(timeout=10)
    pg.terminate()
    try:pg.wait(timeout=10)
    except subprocess.TimeoutExpired:pg.kill();pg.wait()
