
from typing import Tuple
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from .context_store import RedisContextStore
from .agents import AIAgent

class ChatOrchestrator:
    def __init__(self, agent: AIAgent, context_store: RedisContextStore):
        self.agent = agent
        self.context_store = context_store

    async def handle(self, user_msg: str, cid: str, email: str) -> Tuple[str, str]:
        history = await self.context_store.load(cid)
        reply = await self.agent.reply(user_msg, history)
        history.append(HumanMessage(content=user_msg))
        history.append(AIMessage(content=reply))
        await self.context_store.save(cid, history)
        return reply, cid
