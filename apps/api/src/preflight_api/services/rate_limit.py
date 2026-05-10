import time

from redis.asyncio import Redis

from preflight_api.config import get_settings


async def check_rate_limit(redis: Redis, key_fingerprint: str) -> tuple[bool, int]:
    """
    Fixed-window per-minute counter. Returns (allowed, remaining).
    """
    limit = max(1, get_settings().rate_limit_per_minute)
    window = int(time.time() // 60)
    redis_key = f"ratelimit:{key_fingerprint}:{window}"
    count = await redis.incr(redis_key)
    if count == 1:
        await redis.expire(redis_key, 70)
    remaining = max(0, limit - int(count))
    return int(count) <= limit, remaining
