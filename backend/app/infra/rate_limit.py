import logging
import time

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RateLimiter:
    """Fixed window counter in Redis: at most `limit` hits per `window_sec` per key."""

    def __init__(self, redis: Redis, *, limit: int, window_sec: int) -> None:
        self._redis = redis
        self._limit = limit
        self._window = window_sec

    async def hit(self, key: str) -> bool:
        window = int(time.time()) // self._window
        bucket = f"rate:{key}:{window}"
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(bucket)
                pipe.expire(bucket, self._window)
                count, _ = await pipe.execute()
        except RedisError:
            # Fail open: a Redis outage must not lock every user out of login.
            logger.warning("rate limiter unavailable, request allowed", exc_info=True)
            return True
        return int(count) <= self._limit
