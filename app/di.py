from pathlib import Path
from dotenv import load_dotenv
import os, uuid, redis.asyncio as aioredis
from langchain_openai import ChatOpenAI
from fastapi import Depends, Header
from .prompt_builder import PromptBuilder
from .response_parser import ResponseParser
from .agents import AIAgent
from .context_store import RedisContextStore
from .orchestrator import ChatOrchestrator

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