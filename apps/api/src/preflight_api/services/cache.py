import hashlib
import json
from typing import Any

from redis.asyncio import Redis

from preflight_api.config import get_settings


def cache_key_for_request(payload: dict[str, Any], tenant_fingerprint: str | None = None) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if tenant_fingerprint:
        canonical = f"{tenant_fingerprint}|{canonical}"
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"preflight:eval:{digest}"


async def get_cached_eval(
    redis: Redis,
    payload: dict[str, Any],
    tenant_fingerprint: str | None = None,
) -> dict[str, Any] | None:
    key = cache_key_for_request(payload, tenant_fingerprint)
    raw = await redis.get(key)
    if not raw:
        return None
    return json.loads(raw)


async def set_cached_eval(
    redis: Redis,
    payload: dict[str, Any],
    response: dict[str, Any],
    tenant_fingerprint: str | None = None,
) -> None:
    ttl = get_settings().evaluate_cache_ttl_seconds
    key = cache_key_for_request(payload, tenant_fingerprint)
    await redis.setex(key, ttl, json.dumps(response))
