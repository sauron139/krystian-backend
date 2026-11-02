"""Fixed-window rate limiting in Redis: INCR a per-window counter, EXPIRE it on first hit."""

import logging

from redis.exceptions import RedisError

from app.core.errors import too_many_requests
from app.core.redis import redis_client

log = logging.getLogger(__name__)


async def enforce(key: str, limit: int, window_seconds: int) -> None:
    """Raise 429 once `key` has been hit more than `limit` times in the current window."""
    full_key = f"rate:{key}"
    try:
        count = await redis_client.incr(full_key)
        if count == 1:
            await redis_client.expire(full_key, window_seconds)
        if count > limit:
            ttl = await redis_client.ttl(full_key)
            raise too_many_requests(max(ttl, 1))
    except RedisError:
        # Fail open: an outage of the limiter shouldn't take the site down.
        log.warning("rate limiter unavailable for %s", key, exc_info=True)


async def reset(key: str) -> None:
    try:
        await redis_client.delete(f"rate:{key}")
    except RedisError:
        log.warning("rate limiter reset failed for %s", key, exc_info=True)
