
from typing import Union, Dict, Any
from langchain.schema.output_parser import StrOutputParser

class ResponseParser(StrOutputParser):
    """Very thin wrapper; LangChain's built‑ins already parse tool calls."""
    pass
