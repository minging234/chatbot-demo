from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from typing import Any, Dict

from .cal_client import CalComClient, BookingPayload
from .cal_client import CalComClient
import asyncio


class CreateBookingTool(BaseTool):
    name: str = "create_booking"
    description: str = (
        "Creates a new Cal.com booking. "
        "Input must match the BookingPayload schema."
    )
    client: CalComClient

    def _run(  # sync wrapper required by BaseTool
        self, payload: Dict[str, Any], run_manager: CallbackManagerForToolRun | None = None
    ) -> Dict[str, Any]:
        return asyncio.run(self._arun(payload))  # delegate to async version

    async def _arun(  # noqa: D401
        self, payload: Dict[str, Any], run_manager: CallbackManagerForToolRun | None = None
    ) -> Dict[str, Any]:
        data = BookingPayload(**payload)  # Pydantic validation
        return await self.client.create_booking(data)

if __name__ == "__main__":
    # Import necessary classes

    # Initialize the CalComClient (provide any required arguments)
    client = CalComClient()

    # Create an instance of the tool
    create_booking_tool = CreateBookingTool(client=client)

    # Example payload matching BookingPayload schema
    payload = {
        "eventTypeId": 2874092,
        "start": "2025-07-21T23:00:00.000Z",          # 16:00 PDT
        "end":   "2025-07-21T23:30:00.000Z",          # 16:30 PDT
        "title": "Intro call",
        "timeZone": "America/Los_Angeles",
        "language": "en",
        "metadata": {},
        "responses": {
            "name":  "Alice Example",
            "email": "alice@example.com",
            "location": {"value": "userPhone", "optionValue": ""}
        }
    }
    # Synchronous call
    result = create_booking_tool._run(payload)
    print(result)

    # Asynchronous call
    async def main():
        result = await create_booking_tool._arun(payload)
        print(result)

    # To run the async example:
    # asyncio.run(main())
