from typing import Dict, Any
from langchain.tools.base import BaseTool
import json
from langchain_core.messages import ToolMessage
from langchain_core.messages import (
    ToolMessage,
)
from zoneinfo import ZoneInfo
from datetime import datetime
import re, json
import tiktoken
from langchain_core.messages import BaseMessage
from typing import List

import tiktoken



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

LOCAL_TZ = ZoneInfo("America/Los_Angeles")

ISO_UTC_RE = re.compile(r'"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"')

def utc_to_pt(iso_utc: str) -> str:
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    return dt.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %I:%M %p PT")

def rewrite_times_for_human(text: str) -> str:
    # Replace every ISO-UTC timestamp inside a JSON blob that you plan to
    # show to the user. Tools still receive the original JSON.
    return ISO_UTC_RE.sub(lambda m: f'"{utc_to_pt(m.group(1))}"', text)


ENC = tiktoken.encoding_for_model("gpt-3.5-turbo")   # or your model

def num_tokens(msg: BaseMessage) -> int:
    return len(ENC.encode(msg.content))

ENC = tiktoken.encoding_for_model("gpt-3.5-turbo")   # or your target model


def num_tokens(msg: BaseMessage) -> int:
    """Rough token estimate for one message’s content."""
    return len(ENC.encode(msg.content or ""))


def prune_history(
    messages: List[BaseMessage],
    max_tokens: int = 12_000,       # leave ~4k-5k for the model’s reply/tools
) -> List[BaseMessage]:
    """
    Keep the system prompt + *most recent* messages that fit into `max_tokens`.

    • The very first message (system prompt) is always preserved.
    • The **newest** ToolMessage (if any) is preserved in full.
    • Older ToolMessages >200 chars are truncated to “[tool-result truncated]”.
    """
    if not messages:
        return messages

    # 1️⃣  Always keep the system prompt
    pruned: List[BaseMessage] = [messages[0]]
    running_total = num_tokens(messages[0])

    # 2️⃣  Walk the conversation backwards (newest → oldest)
    for idx_from_end, msg in enumerate(reversed(messages[1:]), start=1):
        is_last_tool = (
            idx_from_end == 1                     # newest message
            and hasattr(msg, "tool_call_id")      # and it's a tool result
        )

        # --- compress oversized *older* tool messages --------------------
        if (
            hasattr(msg, "tool_call_id")
            and len(msg.content) > 200
            and not is_last_tool                 # keep newest tool intact
        ):
            msg = msg.__class__(
                tool_call_id=getattr(msg, "tool_call_id"),
                content="[tool-result truncated]",
            )

        t = num_tokens(msg)
        if running_total + t > max_tokens:
            break

        # insert just after the system prompt (keeps chronological order)
        pruned.insert(1, msg)
        running_total += t

    return pruned