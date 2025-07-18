from typing import Dict, Any
from langchain.tools.base import BaseTool
import json
from langchain_core.messages import ToolMessage
from langchain_core.messages import (
    ToolMessage,
)


def to_openai_function_dict(tool: BaseTool) -> Dict[str, Any]:
    """Return the exact dict Chat Completions expects."""
    # Pydantic v2: `schema()` is deprecated; use model_json_schema()
    schema = tool.args_schema.model_json_schema()
    return {
        "type": "function",
        "function": {
            "name":        tool.name,
            "description": tool.description or "",
            "parameters":  schema,
        },
    }


def extract_tool_name(call: dict) -> tuple[str, dict, str]:
    """
    Return (tool_name, arguments_dict) from either the *new* or *old* schema.
    """
    # New schema: {"type":"function","function":{"name":...,"arguments":"{...}"}}
    if "function" in call:
        fn = call["function"]
        name = fn["name"]
        # OpenAI returns *stringified* JSON
        args = json.loads(fn["arguments"] or "{}")
    else:  # Old schema: {"name":..., "arguments": {...}}
        name = call["name"]
        args = call.get("arguments", {})
    return name, args, call["id"]

def all_errors(msgs: list[ToolMessage]) -> bool:
    """True if every ToolMessage content starts with '[error]'."""
    return bool(msgs) and all(m.content.lstrip().startswith("[error]") for m in msgs)