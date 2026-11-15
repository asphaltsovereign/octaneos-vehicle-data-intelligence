from contextlib import contextmanager, ExitStack
import os
import threading
import logging
import psycopg
from psycopg.rows import dict_row
from fastapi import HTTPException

# Serializes this single-process demonstration runtime; native PostgreSQL handles concurrent production connections.
_demo_lock=threading.RLock()
_demo_connection=None
_demo_url=None

def demo_mode():
    return os.getenv('OCTANE_ENV','production')=='development' and os.getenv('OCTANE_DEMO')=='1'

def check_config():
    if os.getenv('OCTANE_DEMO')=='1' and not demo_mode():
        raise HTTPException(503,'Demo authentication is forbidden outside development.')
    if not os.getenv('DATABASE_URL'):
        raise HTTPException(503,'Database configuration is required.')
    if not demo_mode():
        if not os.getenv('SUPABASE_URL','').startswith('https://') or not os.getenv('SUPABASE_PUBLISHABLE_KEY'):
            raise HTTPException(503,'Production authentication configuration is required.')
        if os.getenv('OCTANE_ENV','production')!='production':
            raise HTTPException(503,'Select explicit development demo or production configuration.')

@contextmanager
def connection(user_id=None):
    global _demo_connection,_demo_url
    check_config()
    lock=_demo_lock if demo_mode() else __import__('contextlib').nullcontext()
    try:
        with lock, ExitStack() as stack:
            url=os.environ['DATABASE_URL']
            if demo_mode():
                # PGlite is one PostgreSQL session; retain its connection and serialize transactions.
                if _demo_connection is None or _demo_connection.closed or _demo_url!=url:
                    if _demo_connection is not None:_demo_connection.close()
                    _demo_connection=psycopg.connect(url,row_factory=dict_row,cursor_factory=psycopg.ClientCursor,connect_timeout=5,autocommit=True)
                    _demo_url=url
                conn=_demo_connection
            else:
                conn=stack.enter_context(psycopg.connect(url,row_factory=dict_row,cursor_factory=psycopg.ClientCursor,connect_timeout=5,autocommit=True))
            with conn.transaction():
                role=conn.execute('SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
                if not demo_mode() and (role['rolsuper'] or role['rolbypassrls']):
                    raise HTTPException(503,'Database login must not be superuser or bypass RLS.')
                conn.execute('SET LOCAL ROLE sentinel_app')
                conn.execute("SET LOCAL statement_timeout = '10000ms'")
                conn.execute("SELECT set_config('request.jwt.claim.sub',%s,true)",(str(user_id) if user_id else '',))
                yield conn
    except HTTPException:
        raise
    except psycopg.IntegrityError:
        raise HTTPException(409,'Record conflicts with an existing item or an allowed reference.') from None
    except psycopg.Error as exc:
        logging.getLogger(__name__).error('Database failure type=%s sqlstate=%s',type(exc).__name__,exc.sqlstate)
        raise HTTPException(503,'Database operation unavailable. Retry or contact the workshop administrator.') from None

def require_member(conn,workshop_id):
    if not conn.execute('SELECT 1 FROM sentinel.memberships WHERE workshop_id=%s',(workshop_id,)).fetchone():
        raise HTTPException(403,'You do not have access to this workshop.')
