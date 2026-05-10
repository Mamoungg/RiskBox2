from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from preflight_api.db import get_session
from preflight_api.redis_client import get_redis

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
        redis = get_redis()
        if await redis.ping() is not True:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="redis_not_ready")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="dependencies_not_ready",
        ) from exc
    return {"status": "ready"}
