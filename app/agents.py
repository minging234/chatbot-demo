from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage
from typing import List
from .prompt_builder import PromptBuilder
from .response_parser import ResponseParser
import asyncio
from langchain.schema import HumanMessage
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class AIAgent:
    def __init__(self, llm: ChatOpenAI, builder: PromptBuilder, parser: ResponseParser):
        self.llm = llm
        self.builder = builder
        self.parser = parser

    async def reply(self, user_msg: str, context: List[BaseMessage]) -> str:
        prompt = self.builder.build(user_msg, context)
        raw = await self.llm.ainvoke(prompt)
        return self.parser.parse_result([raw])


if __name__ == "__main__":
    async def main():
        llm = ChatOpenAI(model="gpt-3.5-turbo")
        builder = PromptBuilder()
        parser = ResponseParser()
        agent = AIAgent(llm, builder, parser)

        user_msg = "Hello, who won the world cup in 2018?"
        context = [HumanMessage(content="Hi!")]
        response = await agent.reply(user_msg, context)
        print("AI response:", response)

    asyncio.run(main())
