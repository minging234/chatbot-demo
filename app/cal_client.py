import os
import pprint
from typing import List, Dict, Any, Optional
import httpx
from pydantic import BaseModel, EmailStr, Field

CALCOM_BASE_URL = "https://api.cal.com/v1"


class Attendee(BaseModel):
    email: str

class Responses(BaseModel):
    name: str
    email: EmailStr
    smsReminderNumber: str = ""
    location: Dict[str, str] = Field(
        default_factory=lambda: {"value": "userPhone", "optionValue": ""}
    )

class BookingPayload(BaseModel):
    eventTypeId: int = 17
    start: str  # ISO-8601 string
    end: str
    title: str = "Default Title"
    responses: Responses
    timeZone: str           = "Europe/London"   #  ← default, but NOT None
    language: str           = "en"              #  ← default
    metadata: Dict = Field(default_factory=dict)
    status: str             = "PENDING"
    description: str | None = ""
    attendees: List[Attendee] = Field(default_factory=list)


class CalComClient:
    """
    Minimal Cal.com v1 client (query-param authentication).
    """

    BASE_URL = "https://api.cal.com/v1"

    def __init__(self, api_key: str | None = None):
        # prefer env var so you don’t hard-code secrets
        self.api_key = api_key or os.getenv("CALCOM_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No Cal.com API key found ─ set CALCOM_API_KEY in your environment "
                "or pass api_key='…' to CalComClient()."
            )

    # ---------- helper (build full URL with ?apiKey=…) ----------
    def _url(self, path: str) -> tuple[str, dict]:
        """Return (url, params) so every call includes ?apiKey=…"""
        return f"{self.BASE_URL}{path}", {"apiKey": self.api_key}

    # ---------- public method ----------
    async def create_booking(self, payload: BookingPayload) -> dict:
        url, params = self._url("/bookings")
        # async with httpx.AsyncClient() as client:
        #     r = await client.post(url, params=params, json=payload.model_dump())
        #     r.raise_for_status()
        #     return r.json()
        async with httpx.AsyncClient() as client:
            r = await client.post(url, params=params, json=payload.model_dump())
            if r.status_code >= 400:
                # Pretty-print Cal.com's explanation before raising
                try:
                    pprint.pp(r.json())
                except Exception:
                    print(r.text)
                r.raise_for_status()
            return r.json()