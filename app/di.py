from pathlib import Path
from dotenv import load_dotenv
import os, uuid, redis.asyncio as aioredis
from langchain_openai import ChatOpenAI
from fastapi import Depends, Header, Request
from .prompt_builder import PromptBuilder
from .response_parser import ResponseParser
from .agents import AIAgent
from .context_store import RedisContextStore
from .orchestrator import ChatOrchestrator
from .rate_limiter import RedisRateLimiter
from contextlib import asynccontextmanager
from redis.asyncio import Redis
from fastapi import Depends, HTTPException

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Only cache pure functions with hashable args
def redis_pool():
    return aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

def prompt_builder() -> PromptBuilder:
    return PromptBuilder()

def response_parser() -> ResponseParser:
    return ResponseParser()

def ai_agent(
    builder: PromptBuilder = Depends(prompt_builder),
    parser: ResponseParser = Depends(response_parser)
) -> AIAgent:
    return AIAgent(ChatOpenAI(model="gpt-4o-mini"), builder, parser)

def orchestrator(
    agent: AIAgent = Depends(ai_agent)
) -> ChatOrchestrator:
    redis = redis_pool()
    store = RedisContextStore(redis)
    return ChatOrchestrator(agent, store)

def conversation_id_header(x_conversation_id: str | None = Header(None)):
    return x_conversation_id or str(uuid.uuid4())

@asynccontextmanager
async def lifespan(app):
    redis = Redis.from_url("redis://localhost:6379/0")
    app.state.redis = redis
    try:
        yield
    finally:
        await redis.close()

async def get_redis(request: Request) -> Redis:
    return request.app.state.redis            # already set in lifespan()

async def get_rate_limiter(redis: Redis = Depends(get_redis)):
    return RedisRateLimiter(redis)

async def enforce_rate_limit(
    cid: str = Depends(conversation_id_header),
    limiter: RedisRateLimiter = Depends(get_rate_limiter),
):
    if not await limiter.allow(cid):
        raise HTTPException(429, "Rate limit exceeded")