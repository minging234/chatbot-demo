# app/agents.py
from __future__ import annotations

import asyncio
from typing import List, Sequence

from langchain_openai import ChatOpenAI

from app.tools import CancelBookingTool, ListBookingsTool, RescheduleBookingTool
from app.utils import all_errors, extract_tool_name, prune_history, rewrite_times_for_human


from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from langchain.tools.base import BaseTool

from .prompt_builder import PromptBuilder
from .response_parser import ResponseParser
import sys
import asyncio
from app.utils import to_openai_function_dict


class AIAgent:
    """
    Conversation orchestrator.

    Responsibilities
    ----------------
    1. Build prompt  (history + user turn)               -> PromptBuilder
    2. Call LLM with tool schema(s) attached             -> ChatOpenAI
    3. Detect function / tool calls in the LLM reply
    4. Execute those tool calls (in parallel if possible)
    5. Feed tool results back to the LLM, repeat loop
    6. Return final natural-language answer
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        builder: PromptBuilder,
        parser: ResponseParser,
        tools: Sequence[BaseTool] | None = None,
        max_loops: int = 3,
    ) -> None:
        self._llm = llm
        self._builder = builder
        self._parser = parser
        self._tool_map: dict[str, BaseTool] = {t.name: t for t in tools or []}
        self._max_loops = max_loops

    # --------------------------------------------------------------------- #
    # public API
    # --------------------------------------------------------------------- #
    async def reply(
        self, user_msg: str, history: List[BaseMessage] | None = None
    ) -> str:
        """
        Handle ONE user turn, possibly executing tools behind the scenes.

        Parameters
        ----------
        user_msg : str
            Raw user input.
        history : list[BaseMessage] | None
            Previous turns (already role-tagged).

        Returns
        -------
        str
            Final assistant message with all tool calls resolved.

        Raises
        ------
        RuntimeError
            If the model enters an infinite tool-call loop.
        """
        messages: list[BaseMessage] = self._builder.build(user_msg, (history or []))
        print(messages, len(messages))
        print("history", history, len(history) if history else 0)
        print(self._tool_map)

        for _ in range(self._max_loops):
            messages = prune_history(messages)
            llm_reply: AIMessage = await self._llm.ainvoke(
                messages,
                tools=list(to_openai_function_dict(t) for t in self._tool_map.values()),
                tool_choice="auto",
            ) # type: ignore
            messages.append(llm_reply)

            tool_calls = llm_reply.additional_kwargs.get("tool_calls")
            

            if not tool_calls:  # ✅ no function call -- we're done
                llm_reply.content = rewrite_times_for_human(llm_reply.content)
                return llm_reply.content

            # ----------------------------------------------------------------
            # execute requested tools  (parallel if >1)
            # ----------------------------------------------------------------
            parsed_calls = [extract_tool_name(c) for c in tool_calls]

            # separate known vs. unknown tools
            unknown = [
                name for name, *_ in parsed_calls
                if name not in self._tool_map
            ]
            valid_calls = [
                (name, args, call_id)
                for name, args, call_id in parsed_calls
                if name in self._tool_map
            ]

            # --- no recognised tool at all ---------------------------------
            if not valid_calls:
                unknown_str = ", ".join(unknown)
                return (
                    "Sorry — I don’t support that action yet "
                    f"(requested: {unknown_str})."
                )

            # --- run the ones we *do* support ------------------------------
            tool_tasks = [
                self._run_tool(name, args, call_id)
                for name, args, call_id in valid_calls
            ]
            tool_messages = await asyncio.gather(*tool_tasks)
            messages.extend(tool_messages)
            # ─── if every tool failed, surface the validation error to the user ───
            if all_errors(tool_messages):
                # you could merge multiple error strings; here we show only the first
                first_error = tool_messages[0].content
                return (
                    "I couldn’t complete that action:\n\n"
                    f"{first_error}\n\n"
                    "Please revise the information and try again."
                )

        raise RuntimeError("AIAgent exceeded max tool-execution loops")

    # --------------------------------------------------------------------- #
    # helpers
    # --------------------------------------------------------------------- #
    async def _run_tool(self, name: str, args: dict, call_id: str) -> ToolMessage:
        print("running tool")
        print(name, call_id, args, self._tool_map.get(name))
        """Locate the tool, execute it, wrap result as a ToolMessage."""
        tool = self._tool_map.get(name)
        if tool is None:
            return ToolMessage(
                tool_call_id=call_id,
                content=f"[error] Unknown tool: {name}",
            )

        try:
            result = await tool.ainvoke(args)
        except Exception as exc:  # noqa: BLE001
            result = f"[error] {type(exc).__name__}: {exc}"

        return ToolMessage(tool_call_id=call_id, content=str(result))

if __name__ == "__main__":
    from .tools import CreateBookingTool  # assumes you have a 'tools' list in tools.py
    from app.cal_client import CalComClient

    # Initialize the CalComClient (provide any required arguments)
    client = CalComClient()

    # Create an instance of the tool
    create_booking_tool = CreateBookingTool(client=client)
    list_booking_tool = ListBookingsTool(client=client)
    cancel_booking_tool = CancelBookingTool(client=client)
    reschedule_tool = RescheduleBookingTool(client=client)
    tools = [create_booking_tool, list_booking_tool, cancel_booking_tool, reschedule_tool]


    async def main():
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        builder = PromptBuilder()
        parser = ResponseParser()
        agent = AIAgent(llm, builder, parser, tools=tools)

        # user_msg = "What is the weather in Paris and tell me a joke?"
        user_msg = "Book a 30-minute call next Tuesday at 1 PM with alice@example.com. I am in PST time, tile is 'intro chat', location is default "
        # user_msg = "forgot all the previous context, List all the upcoming meeting with Alice, here email is alice@example.com"
        # user_msg = "help me reschedule the meeting for next Monday, 21 Jul 1:00pm - 1:30pm with Grace (grace2@example.com) to the same day 3:00pm - 3:30pm"
        history = []

        reply = await agent.reply(user_msg, history)
        print("Assistant:", reply)

    asyncio.run(main())