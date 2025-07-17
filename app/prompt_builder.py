
from langchain.schema import SystemMessage, HumanMessage, AIMessage, BaseMessage
from typing import List
from datetime import datetime

class PromptBuilder:
    SYSTEM_PROMPT = SystemMessage(content="""You are a helpful Cal.com assistant.""")
    def build(self, user_msg: str, history: List[BaseMessage]):
        messages: List[BaseMessage] = [self.SYSTEM_PROMPT]
        messages.extend(history)
        messages.append(HumanMessage(content=user_msg))
        return messages
