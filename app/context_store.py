
import json, asyncio
from redis.asyncio import Redis
from typing import List
from langchain.schema import BaseMessage

class RedisContextStore:
    def __init__(self, redis: Redis, ttl_seconds: int = 86_400):
        self.redis = redis
        self.ttl = ttl_seconds

    async def load(self, cid: str) -> List[BaseMessage]:
        data = await self.redis.get(cid)
        if not data:
            return []
        return json.loads(data)

    async def save(self, cid: str, messages: List[BaseMessage]):
        await self.redis.set(cid, json.dumps([m.dict() for m in messages]), ex=self.ttl)


