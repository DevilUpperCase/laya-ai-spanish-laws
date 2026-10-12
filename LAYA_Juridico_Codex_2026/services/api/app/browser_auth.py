"""Self-hosted password verification and opaque, revocable HttpOnly sessions."""
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
import hashlib, secrets, time
from uuid import UUID
import httpx
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from .errors import DomainError

router=APIRouter(prefix='/auth',tags=['Browser authentication'])
COOKIE='laya_session'


class Login(BaseModel):
    model_config=ConfigDict(extra='forbid')
    email: str=Field(min_length=3,max_length=254)
    password: str=Field(min_length=1,max_length=1024,repr=False)


class PasswordChange(Login):
    new_password: str=Field(min_length=12,max_length=1024,repr=False)


def csrf_allowed(request):
    return request.headers.get('origin') in request.app.state.settings.cors_origins and request.headers.get('x-requested-with')=='LAYA'


async def session_identity(request: Request):
    value=request.cookies.get(COOKIE,'')
    if len(value)!=43 or request.app.state.db is None:raise DomainError('AUTH_REQUIRED',401)
    digest=hashlib.sha256(value.encode()).hexdigest()
    async with request.app.state.db.pool.connection() as conn:
        row=await (await conn.execute('SELECT user_id,email,expires_at FROM browser_auth.sessions WHERE digest=%s AND expires_at>now()',(digest,))).fetchone()
    if row is None:raise DomainError('AUTH_INVALID',401)
    return row


async def workspaces(request,user_id):
    async with request.app.state.db.pool.connection() as conn:
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.user_id',%s,true)",(str(user_id),))
            return await (await conn.execute('SELECT * FROM private.my_workspaces()')).fetchall()


async def verify_password(request,body):
    settings=request.app.state.settings
    if not settings.supabase_auth_url or request.app.state.db is None:raise DomainError('AUTH_UNAVAILABLE',503)
    # Bound brute force before contacting Auth; never store email/password in attempt telemetry.
    attempts=request.app.state.login_attempts
    now=time.monotonic();key=request.client.host if request.client else 'unknown'
    queue=attempts[key]
    while queue and queue[0]<now-60:queue.popleft()
    if len(queue)>=10:raise DomainError('AUTH_RATE_LIMIT',429)
    queue.append(now)
    if len(attempts)>10000:
        for old in list(attempts):
            if not attempts[old] or attempts[old][-1]<now-60:del attempts[old]
    try:
        async with httpx.AsyncClient(base_url=settings.supabase_auth_url,trust_env=False,timeout=15) as client:
            response=await client.post('/token',params={'grant_type':'password'},json={'email':body.email.strip(),'password':body.password})
            if response.status_code in {400,401,422}:raise DomainError('AUTH_INVALID',401)
            if response.status_code!=200:raise DomainError('AUTH_UNAVAILABLE',503)
            # Verify the returned identity with the private Auth service, not a client assertion.
            token=response.json()['access_token']
            verified=await client.get('/user',headers={'Authorization':'Bearer '+token})
            if verified.status_code!=200:raise DomainError('AUTH_INVALID',401)
            user=verified.json();user_id=UUID(user['id'])
            if user.get('banned_until') or not user.get('email_confirmed_at'):raise DomainError('AUTH_INVALID',401)
            return user_id,user['email'],token
    except (httpx.HTTPError,ValueError,KeyError,TypeError):raise DomainError('AUTH_UNAVAILABLE',503) from None


@router.post('/login')
async def login(body:Login,request:Request,response:Response):
    user_id,email,_=await verify_password(request,body)
    tenants=await workspaces(request,user_id)
    if not tenants:raise DomainError('TENANT_FORBIDDEN',403)
    token=secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest()
    expires=datetime.now(timezone.utc)+timedelta(seconds=request.app.state.settings.browser_session_seconds)
    async with request.app.state.db.pool.connection() as conn:
        await conn.execute('DELETE FROM browser_auth.sessions WHERE expires_at<=now()')
        # Limit active sessions for this user; preserves independent sessions within the bound.
        await conn.execute('DELETE FROM browser_auth.sessions WHERE digest IN (SELECT digest FROM browser_auth.sessions WHERE user_id=%s ORDER BY created_at DESC OFFSET 9)',(user_id,))
        await conn.execute('INSERT INTO browser_auth.sessions(digest,user_id,email,expires_at) VALUES(%s,%s,%s,%s)',(digest,user_id,email,expires))
    response.set_cookie(COOKIE,token,httponly=True,secure=request.app.state.settings.app_env=='production',samesite='strict',max_age=request.app.state.settings.browser_session_seconds,path='/')
    return {'email':email,'tenants':tenants,'expires_at':expires}


@router.get('/session')
async def current_session(request:Request):
    identity=await session_identity(request)
    tenants=await workspaces(request,identity['user_id'])
    if not tenants:raise DomainError('TENANT_FORBIDDEN',403)
    return {'email':identity['email'],'tenants':tenants,'expires_at':identity['expires_at']}


@router.post('/logout',status_code=204)
async def logout(request:Request,response:Response):
    value=request.cookies.get(COOKIE,'')
    if request.app.state.db and value:
        async with request.app.state.db.pool.connection() as conn:
            await conn.execute('DELETE FROM browser_auth.sessions WHERE digest=%s',(hashlib.sha256(value.encode()).hexdigest(),))
    response.delete_cookie(COOKIE,path='/',httponly=True,samesite='strict',secure=request.app.state.settings.app_env=='production')


@router.post('/password',status_code=204)
async def change_password(body:PasswordChange,request:Request,response:Response):
    identity=await session_identity(request)
    user_id,_,access_token=await verify_password(request,body)
    if user_id!=identity['user_id']:raise DomainError('AUTH_INVALID',401)
    async with httpx.AsyncClient(base_url=request.app.state.settings.supabase_auth_url,trust_env=False,timeout=15) as client:
        changed=await client.put('/user',headers={'Authorization':'Bearer '+access_token},json={'password':body.new_password})
        if changed.status_code!=200:raise DomainError('PASSWORD_REJECTED',400)
    async with request.app.state.db.pool.connection() as conn:
        await conn.execute('DELETE FROM browser_auth.sessions WHERE user_id=%s',(user_id,))
    response.delete_cookie(COOKIE,path='/',httponly=True,samesite='strict',secure=request.app.state.settings.app_env=='production')
