import hashlib
import os
import secrets
import time
from collections import defaultdict,deque
from uuid import UUID
import httpx
from fastapi import Header,HTTPException,Request
from .db import demo_mode,check_config

DEMO_USER=UUID('d0000000-0000-4000-8000-000000000001')
_sessions={}
_revoked={}
_limits=defaultdict(deque)

def rate_limit(key,limit=30,seconds=60):
    now=time.monotonic()
    if len(_limits)>5000:
        for k in list(_limits):
            if not _limits[k] or _limits[k][-1]<now-seconds: del _limits[k]
        if len(_limits)>5000: raise HTTPException(429,'Service busy. Retry in a minute.')
    q=_limits[key]
    while q and q[0]<=now-seconds:q.popleft()
    if len(q)>=limit: raise HTTPException(429,'Request limit reached. Retry in a minute.')
    q.append(now)

def demo_login():
    if not demo_mode():raise HTTPException(404,'Demo mode is disabled.')
    now=time.time()
    for k in list(_sessions):
        if _sessions[k]<now:del _sessions[k]
    if len(_sessions)>1000:raise HTTPException(429,'Demo session limit reached.')
    token=secrets.token_urlsafe(40)
    _sessions[hashlib.sha256(token.encode()).hexdigest()]=now+28800
    return {'access_token':token,'expires_in':28800}

def bearer(authorization):
    if not authorization or not authorization.startswith('Bearer ') or len(authorization)>8192:
        raise HTTPException(401,'Sign in to continue.')
    return authorization[7:]

async def supabase_request(method,path,token=None,payload=None):
    check_config()
    headers={'apikey':os.environ['SUPABASE_PUBLISHABLE_KEY']}
    if token:headers['Authorization']='Bearer '+token
    try:
        async with httpx.AsyncClient(timeout=8.0,follow_redirects=False) as client:
            response=await client.request(method,os.environ['SUPABASE_URL'].rstrip('/')+'/auth/v1/'+path,headers=headers,json=payload)
        if response.status_code>=500:raise HTTPException(503,'Sign-in service unavailable. Retry shortly.')
        if response.status_code>=400:raise HTTPException(401,'Session expired or credentials were not accepted.')
        return response.json() if response.content else {}
    except httpx.HTTPError:
        raise HTTPException(503,'Sign-in service unavailable. Retry shortly.') from None

async def authenticated_user(authorization:str|None=Header(default=None)):
    token=bearer(authorization)
    digest=hashlib.sha256(token.encode()).hexdigest()
    now=time.time()
    if _revoked.get(digest,0)>now:raise HTTPException(401,'Session ended. Sign in again.')
    if demo_mode():
        if _sessions.get(digest,0)<=now:raise HTTPException(401,'Demo session expired. Sign in again.')
        return DEMO_USER
    data=await supabase_request('GET','user',token)
    try:return UUID(data['id'])
    except (KeyError,ValueError,TypeError):raise HTTPException(401,'Identity verification failed.') from None

async def logout(authorization):
    token=bearer(authorization)
    digest=hashlib.sha256(token.encode()).hexdigest()
    if demo_mode():_sessions.pop(digest,None)
    else:
        await supabase_request('POST','logout?scope=local',token)
        # A server-validated session revocation plus local immediate access-token denial.
        now=time.time()
        for k in list(_revoked):
            if _revoked[k]<=now:del _revoked[k]
        _revoked[digest]=now+86400
