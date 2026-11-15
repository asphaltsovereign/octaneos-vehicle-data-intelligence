"""ASGI request boundaries apply before multipart parsing and legacy routes."""
from fastapi import HTTPException
from starlette.responses import JSONResponse
from .db import demo_mode,connection,require_member
from .auth import authenticated_user
from uuid import UUID

class BodyLimit(Exception):pass
class WorkshopBoundary:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        path=scope['path']
        if not demo_mode() and path in {'/demo','/analyze','/explain','/model/validate','/submission/status','/model/info','/scenarios','/ai/status'}:
            return await JSONResponse({'detail':'Legacy laboratory endpoints are disabled in production.'},404)(scope,receive,send)
        headers={k.decode().lower():v.decode() for k,v in scope.get('headers',[])}
        max_size=2*1024*1024+65536 if path.endswith('/analyze') else 65536
        if path.startswith('/api/') and scope['method'] in ('POST','PUT','PATCH'):
            try:
                length=int(headers.get('content-length','0'))
                if length<0 or length>max_size:raise BodyLimit()
            except (ValueError,BodyLimit):
                return await JSONResponse({'detail':'Request exceeds the allowed size.'},413)(scope,receive,send)
        # Authentication precedes upload parsing, even when FastAPI declares UploadFile.
        # Dependencies are called again at the route boundary to prevent trusting request state.
        if path.startswith('/api/jobs/') and path.endswith('/analyze'):
            try:
                user=await authenticated_user(headers.get('authorization'))
                workshop=UUID(headers.get('x-workshop-id',''))
                with connection(user) as conn:require_member(conn,workshop)
            except (HTTPException,ValueError) as exc:
                status=exc.status_code if isinstance(exc,HTTPException) else 422
                detail=exc.detail if isinstance(exc,HTTPException) else 'Select a workshop.'
                return await JSONResponse({'detail':detail},status)(scope,receive,send)
        total=0
        async def bounded_receive():
            nonlocal total
            message=await receive()
            if message['type']=='http.request':
                total+=len(message.get('body',b''))
                if path.startswith('/api/') and total>max_size:raise BodyLimit()
            return message
        async def secure_send(message):
            if message['type']=='http.response.start':
                h=list(message.get('headers',[]))
                h.extend([(b'x-content-type-options',b'nosniff'),(b'referrer-policy',b'no-referrer'),(b'x-frame-options',b'DENY'),(b'cache-control',b'no-store')])
                # Dev lab uses inline charts; production default has no inline scripts.
                if not demo_mode():h.append((b'content-security-policy',b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"))
                message['headers']=h
            await send(message)
        try:await self.app(scope,bounded_receive,secure_send)
        except BodyLimit:
            await JSONResponse({'detail':'Request exceeds the allowed size.'},413)(scope,receive,send)
