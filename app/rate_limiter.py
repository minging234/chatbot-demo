
from redis.asyncio import Redis
from datetime import datetime, timedelta

class RedisRateLimiter:
    def __init__(self, redis: Redis, limit: int = 20, window_sec: int = 60):
        self.redis = redis
        self.limit = limit
        self.window = window_sec

    async def allow(self, key: str) -> bool:
        now = int(datetime.utcnow().timestamp())
        window_key = f"rate:{key}:{now // self.window}"
        current = await self.redis.incr(window_key)
        if current == 1:
            await self.redis.expire(window_key, self.window)
        return current <= self.limit
