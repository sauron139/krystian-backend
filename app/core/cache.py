"""Redis cache for public reads.

Invalidation uses a version counter: every key includes the current version, and any admin
write bumps it. That invalidates the whole public cache in O(1) without scanning keys; stale
entries simply expire via their TTL. Redis outages degrade to uncached reads, never errors.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, cast

from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.redis import redis_client

log = logging.getLogger(__name__)
VERSION_KEY = "public-cache:version"


async def cached(key: str, loader: Callable[[], Awaitable[Any]]) -> Any:
    """Return the JSON-able value for `key`, computing it with `loader` on a miss."""
    try:
        # The client uses decode_responses=True, so values come back as str.
        version = cast(str | None, await redis_client.get(VERSION_KEY)) or "0"
        full_key = f"public-cache:v{version}:{key}"
        hit = await redis_client.get(full_key)
        if hit is not None:
            return json.loads(hit)
    except RedisError:
        log.warning("cache read failed for %s", key, exc_info=True)
        return await loader()

    value = await loader()
    try:
        await redis_client.set(
            full_key, json.dumps(value), ex=get_settings().public_cache_ttl_seconds
        )
    except RedisError:
        log.warning("cache write failed for %s", key, exc_info=True)
    return value


async def invalidate_public_cache() -> None:
    try:
        await redis_client.incr(VERSION_KEY)
    except RedisError:
        log.error("cache invalidation failed; public data may be stale until TTL", exc_info=True)
