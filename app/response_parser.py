
from typing import List, Union, Dict, Any
from langchain.schema.output_parser import StrOutputParser
from langchain.schema import BaseMessage

class ResponseParser(StrOutputParser):
    """Very thin wrapper; LangChain's built‑ins already parse tool calls."""
    def parse_result(self, result: List[BaseMessage]) -> str:
        content = result[0].content
        if not isinstance(content, str):
            content = str(content)
        return content
