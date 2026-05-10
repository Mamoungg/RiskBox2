from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from preflight_api.db import get_session
from preflight_api.redis_client import get_redis
from preflight_api.security import hash_api_key
from preflight_api.services.auth import validate_api_key
from preflight_api.services.rate_limit import check_rate_limit


async def require_api_key(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_api_key")
    if not await validate_api_key(session, x_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_api_key")

    redis = get_redis()
    fingerprint = hash_api_key(x_api_key)[:16]
    allowed, remaining = await check_rate_limit(redis, fingerprint)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate_limit_exceeded",
            headers={"X-RateLimit-Remaining": str(remaining)},
        )
    request.state.api_key_fingerprint = fingerprint
    return x_api_key
