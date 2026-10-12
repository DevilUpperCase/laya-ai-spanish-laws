import asyncio
from uuid import UUID
import jwt
from fastapi import Header, Request
from jwt import PyJWKClient
from .contracts import TenantContext
from .errors import DomainError


class Authenticator:
    def __init__(self, settings):
        self.settings = settings
        self.jwks = PyJWKClient(settings.auth_jwks_url, cache_keys=True, lifespan=300) if settings.auth_jwks_url else None

    async def verify(self, token: str) -> UUID:
        try:
            if len(token) > 8192:
                raise ValueError()
            key = (await asyncio.to_thread(self.jwks.get_signing_key_from_jwt, token)).key if self.jwks else self.settings.auth_public_key_path.read_bytes()
            claims = jwt.decode(token, key, algorithms=["RS256"], audience=self.settings.auth_audience,
                                issuer=self.settings.auth_issuer, options={"require": ["exp", "iat", "iss", "aud", "sub"]})
            return UUID(claims["sub"])
        except (jwt.PyJWTError, ValueError, OSError, KeyError, TypeError):
            raise DomainError("AUTH_INVALID", 401) from None


async def require_context(request: Request, authorization: str | None = Header(default=None),
                          x_tenant_id: str | None = Header(default=None)) -> TenantContext:
    if authorization:
        if not authorization.startswith('Bearer '):raise DomainError('AUTH_REQUIRED',401)
        user_id=await request.app.state.auth.verify(authorization[7:])
    else:
        from .browser_auth import session_identity
        user_id=(await session_identity(request))['user_id']
    try:
        tenant_id = UUID(x_tenant_id or "")
    except ValueError:
        raise DomainError("TENANT_REQUIRED", 403) from None
    db = request.app.state.db
    if db is None:
        raise DomainError("DATABASE_UNAVAILABLE", 503)
    role = await db.resolve_membership(user_id, tenant_id)
    if role is None:
        raise DomainError("TENANT_FORBIDDEN", 403)
    return TenantContext(user_id=user_id, tenant_id=tenant_id, role=role)
