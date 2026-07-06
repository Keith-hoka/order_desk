"""JWT bearer authentication for the extraction API (Phase 4).

HS256 symmetric signing with a single secret from JWT_SECRET. When the
secret is unset, auth is disabled -- a dev/test convenience, never a
production default (Docker Compose ships a secret, and the deploy docs
require one). Only business endpoints are guarded; /health and /ready stay
open so infra probes can reach them.

Claims are minimal: sub (client id), exp (expiry), iat. Scopes/roles are
deferred to the multi-tenant Phase 11, where they are actually needed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ALGORITHM = "HS256"
DEFAULT_TTL_SECONDS = 3600

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    sub: str


def issue_token(secret: str, sub: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    now = int(time.time())
    payload = {"sub": sub, "iat": now, "exp": now + ttl_seconds}
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_token(secret: str, token: str) -> Principal:
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise HTTPException(status_code=401, detail="token missing subject")
    return Principal(sub=sub)


def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal | None:
    """Guard dependency: enforce a valid bearer token when a secret is set."""
    secret = getattr(request.app.state, "jwt_secret", "")
    if not secret:
        return None  # auth disabled (no secret configured)
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(secret, credentials.credentials)
