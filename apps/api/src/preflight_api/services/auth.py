from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from preflight_api.config import get_settings
from preflight_api.models import ApiKey
from preflight_api.security import constant_time_equals, hash_api_key


def env_api_keys() -> list[str]:
    raw = get_settings().sandbox_api_keys.strip()
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


async def validate_api_key(session: AsyncSession | None, raw_key: str | None) -> bool:
    if not raw_key:
        return False
    for candidate in env_api_keys():
        if constant_time_equals(candidate, raw_key):
            return True
    if session is None:
        return False
    digest = hash_api_key(raw_key)
    stmt = select(ApiKey).where(ApiKey.key_hash == digest, ApiKey.revoked.is_(False))
    res = await session.execute(stmt)
    return res.scalar_one_or_none() is not None
