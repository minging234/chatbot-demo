from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage
from typing import List
from .prompt_builder import PromptBuilder
from .response_parser import ResponseParser

class AIAgent:
    def __init__(self, llm: ChatOpenAI, builder: PromptBuilder, parser: ResponseParser):
        self.llm = llm
        self.builder = builder
        self.parser = parser

    async def reply(self, user_msg: str, context: List[BaseMessage]) -> str:
        prompt = self.builder.build(user_msg, context)
        raw = await self.llm.ainvoke(prompt)
        return self.parser.parse_result(raw)
