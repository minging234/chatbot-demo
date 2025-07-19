from langchain.tools import BaseTool
from langchain.callbacks.manager import CallbackManagerForToolRun
from typing import Any, ClassVar, Dict, Optional, Type

from pydantic import BaseModel, PrivateAttr

from .cal_client import CalComClient, BookingPayload
from .cal_client import CalComClient
import asyncio


class CreateBookingTool(BaseTool):
    name: str = "create_booking"
    description: str = (
        "Creates a new Cal.com booking. "
        "Input must match the BookingPayload schema."
    )
    _client: CalComClient = PrivateAttr()
    args_schema: ClassVar[Type[BaseModel]] = BookingPayload

    # ------------------------------------------------------------------ #
    # constructor
    # ------------------------------------------------------------------ #
    def __init__(self, client: CalComClient, **data: Any) -> None:  # noqa: D401
        super().__init__(**data)
        self._client = client

    def _run(  # sync wrapper required by BaseTool
        self, payload: Dict[str, Any], run_manager: CallbackManagerForToolRun | None = None
    ) -> Dict[str, Any]:
        return asyncio.run(self._arun(run_manager=run_manager, **payload))  # delegate to async version

    # ------------------------------------------------------------------ #
    # async runner (langchain will call this from .run or .arun)
    # ------------------------------------------------------------------ #
    async def _arun(
        self, 
        run_manager: CallbackManagerForToolRun | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        data = BookingPayload(**kwargs)   # validates & coerces
        return await self._client.create_booking(data) # type: ignore


class ListBookingsArgs(BaseModel):
    """Arguments for ``list_bookings``.

    All time values must be **absolute ISO‑8601** (UTC or offset) strings.  You
    can leave the optional filters empty to fetch *all* bookings for the
    attendee.
    """

    attendeeEmail: str
    afterStart: Optional[str] = None  # e.g. "2025-07-18T15:00:00-07:00"
    beforeEnd: Optional[str] = None   # e.g. "2025-07-18T16:00:00-07:00"
    status: Optional[str] = "upcoming" 


class CancelBookingArgs(BaseModel):
    """Arguments for ``cancel_booking``."""

    booking_uid: str
    cancellation_reason: Optional[str] = None
    all_remaining_bookings: Optional[bool] = False


class ListBookingsTool(BaseTool):
    name: str = "list_bookings"
    description: str = (
        "Returns every scheduled Cal.com event where the invitee’s e‑mail "
        "matches the given address. Optional filters: after_start, before_end, "
        "status (ACCEPTED, CANCELLED, ...)."
    )
    _client: CalComClient = PrivateAttr()
    args_schema: ClassVar[Type[BaseModel]] = ListBookingsArgs

    def __init__(self, client: CalComClient, **data: Any) -> None:
        super().__init__(**data)
        self._client = client

    # sync wrapper required by BaseTool
    def _run(self, payload: Dict[str, Any],
             run_manager: CallbackManagerForToolRun | None = None) -> Dict[str, Any]:
        return asyncio.run(self._arun(**payload))

    async def _arun(
        self,
        attendeeEmail: str,
        afterStart: str | None = None,
        beforeEnd: str | None = None,
        status: str | None = None,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> Dict[str, Any]:
        return await self._client.list_bookings(
            email=attendeeEmail,
            after_start=afterStart,
            before_end=beforeEnd,
            status=status, # type: ignore
        ) 


class CancelBookingTool(BaseTool):
    """Cancel an existing booking identified by its UID."""

    name: str = "cancel_booking"
    description: str = (
        "Cancels a Cal.com booking identified by its `booking_uid`. "
        "Optional fields: `cancellation_reason`, `all_remaining_bookings` to "
        "cancel an entire recurring series."
    )
    args_schema: ClassVar[Type[BaseModel]] = CancelBookingArgs

    _client: CalComClient = PrivateAttr()

    def __init__(self, client: CalComClient, **data: Any):
        super().__init__(**data)
        self._client = client

    # -------- sync wrapper --------------------------------------------------
    def _run(
        self,
        payload: Dict[str, Any],
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> Dict[str, Any]:
        return asyncio.run(self._arun(**payload))

    # -------- async impl ----------------------------------------------------
    async def _arun(
        self,
        booking_uid: str,
        cancellation_reason: str | None = None,
        all_remaining_bookings: bool = False,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> Dict[str, Any]:
        return await self._client.cancel_booking(
            booking_uid=booking_uid,
            cancellation_reason=cancellation_reason,
            all_remaining_bookings=all_remaining_bookings,
        )


if __name__ == "__main__":
    # Import necessary classes

    # Initialize the CalComClient (provide any required arguments)
    client = CalComClient()

    # Create an instance of the tool
    create_booking_tool = CreateBookingTool(client=client)

    # Example payload matching BookingPayload schema
    # payload = {
    #     "eventTypeId": 2874092,
    #     "start": "2025-07-21T23:00:00.000Z",          # 16:00 PDT
    #     "end":   "2025-07-21T23:30:00.000Z",          # 16:30 PDT
    #     "title": "Intro call",
    #     "timeZone": "America/Los_Angeles",
    #     "language": "en",
    #     "metadata": {},
    #     "responses": {
    #         "name":  "Alice Example",
    #         "email": "alice@example.com",
    #         "location": {"value": "userPhone", "optionValue": ""}
    #     }
    # }
    # # Synchronous call
    # result = create_booking_tool._run(payload)
    # print(result)

    # # Asynchronous call
    # async def main():
    #     result = await create_booking_tool._arun(payload)
    #     print(result)

    # To run the async example:
    # asyncio.run(main())


    # Create an instance of the ListBookingTool
    query_schedule_tool = ListBookingsTool(client=client)

    # Example email to query schedules
    # email = "grace2@example.com"
    email = "alice@example.com"
    payload = {'attendeeEmail': email, 'afterStart': '2025-07-21T17:00:00Z', 'beforeEnd': '2025-07-21T19:00:00Z'} 

    # Synchronous call to list schedules
    schedule_result = query_schedule_tool._run(payload)
    print(schedule_result)



    # -----------------------------------

    cancel_meeting_tool = CancelBookingTool(client=client)

    # Example email to query schedules
    # email = "grace2@example.com"
    email = "alice@example.com"

    # Synchronous call to list schedules
    cancel_result = cancel_meeting_tool._run({"booking_uid": 'bXAGaUL4sbrEfQQ6gatkBC', "cancellation_reason": "test"})
    print(cancel_result)
