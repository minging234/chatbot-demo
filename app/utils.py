from typing import Dict, Any
from langchain.tools.base import BaseTool
import json
from langchain_core.messages import ToolMessage
from langchain_core.messages import (
    ToolMessage,
)


def to_openai_function_dict(tool: BaseTool) -> Dict[str, Any]:
    """
    Build the dict that Chat Completions expects for a single function/tool,
    working with either Pydantic v1 or v2 and tolerating tools that have no
    input schema.
    """
    if not getattr(tool, "args_schema", None):
        schema: Dict[str, Any] = {"type": "object", "properties": {}}
    else:
        schema = (
            tool.args_schema.model_json_schema()             # Pydantic ≥ 2.0
            if hasattr(tool.args_schema, "model_json_schema")
            else tool.args_schema.schema()                   # Pydantic 1.x
        )

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