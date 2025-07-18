
import json, asyncio
from redis.asyncio import Redis
from typing import List
from langchain.schema import BaseMessage
import os
import asyncio
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.messages import (          
    messages_to_dict,
    messages_from_dict,
)
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory

class RedisContextStore:
    def __init__(self, redis: Redis, ttl_seconds: int = 86_400):
        self.redis = redis
        self.ttl = ttl_seconds

    @staticmethod
    def get_memory(
        cid: str,
    ) -> ConversationBufferMemory:
        chat_hist = RedisChatMessageHistory(
            url="redis://localhost:6379/0",   # or os.getenv("REDIS_URL", "...")
            session_id=cid,
            key_prefix="chat",                # chat:<cid>:messages
            ttl=86_400,                       # 1 day
        )
        return ConversationBufferMemory(
            chat_memory=chat_hist,
            return_messages=True,             # agent gets BaseMessage objects
        )

    async def save(self, cid: str, messages: List[BaseMessage]):
        data = json.dumps(messages_to_dict(messages))
        await self.redis.set(cid, data, ex=self.ttl)

    async def load(self, cid: str) -> List[BaseMessage]:
        data = await self.redis.get(cid)
        if not data:
            return []
        messages_dict = json.loads(data)
        return messages_from_dict(messages_dict)


if __name__ == "__main__":

    async def main():
        # Connect to Redis (default localhost:6379)
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis = Redis.from_url(redis_url)

        store = RedisContextStore(redis)

        cid = "test_conversation"
        messages = [
            HumanMessage(content="Hello!"),
            AIMessage(content="Hi, how can I help you?")
        ]

        # Save messages
        await store.save(cid, messages)

        # Load messages
        loaded = await store.load(cid)
        print("Loaded messages:", loaded)

        # Cleanup
        await redis.delete(cid)
        await redis.close()

    asyncio.run(main())
