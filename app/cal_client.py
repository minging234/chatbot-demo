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


class BookingResult(BaseModel):
    ok: bool                      # True if HTTP 2xx
    status: int                   # HTTP status code
    data: Optional[Dict[str, Any]] = None   # successful JSON body
    error: Optional[str] = None              # short reason
    raw: Optional[Dict[str, Any]] = None     # full server payload



class CalComClient:
    """
    Minimal Cal.com v1 client (query-param authentication).
    """

    BASE_URL = "https://api.cal.com/v1"
    BASE_URL_V2 = "https://api.cal.com/v2"
    _API_VERSION = "2024-08-13"

    def __init__(self, api_key: str | None = None):
        # prefer env var so you don’t hard-code secrets
        self.api_key = api_key or os.getenv("CALCOM_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No Cal.com API key found ─ set CALCOM_API_KEY in your environment "
                "or pass api_key='…' to CalComClient()."
            )

    # ---------- helper (build full URL with ?apiKey=…) ----------
    def _url(self, path: str, use_v2=False) -> tuple[str, dict]:
        """Return (url, params) so every call includes ?apiKey=…"""
        if use_v2:
            return f"{self.BASE_URL_V2}{path}", {}
        return f"{self.BASE_URL}{path}", {"apiKey": self.api_key}
    
    def _auth_headers(self) -> dict:
        """Headers for all /v2/* calls."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "cal-api-version": self._API_VERSION,
        }

    # ---------- public method ----------
    async def create_booking(self, payload: BookingPayload) -> BookingResult:
        """
        Make the booking request and *always* return a BookingResult.
        No exceptions are bubbled up to the caller.
        """
        url, params = self._url("/bookings")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, params=params,
                                          json=payload.model_dump())
            except httpx.RequestError as exc:
                # Network / DNS / TLS failure
                return BookingResult(
                    ok=False, status=0,
                    error=f"Network error: {exc}",
                )

        # ---- We got an HTTP response ----
        status = resp.status_code
        try:
            body = resp.json()
        except ValueError:
            body = {"raw_text": resp.text or "<empty>"}

        if 200 <= status < 300:
            return BookingResult(ok=True, status=status, data=body)

        # Pretty-print once for local debugging (optional)
        pprint.pprint(body)

        # Build a concise error string
        error_msg = body.get("message") or body.get("error") or resp.reason_phrase
        return BookingResult(
            ok=False,
            status=status,
            error=error_msg,
            raw=body,
        )

    # ─────────────────────────────────────────────────────────────
    # NEW: fetch existing bookings for a given invitee e-mail
    # ─────────────────────────────────────────────────────────────
    async def list_bookings(self, attendee_email: str) -> BookingResult:
        """
        Return every booking whose *invitee* matches `attendee_email`.
        """
        url, params = self._url("/bookings", use_v2=True)
        params["attendeeEmail"] = attendee_email
        params["status"] = "upcoming"
        headers = self._auth_headers()

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, headers=headers)
            except httpx.RequestError as exc:           # network/DNS failure
                return BookingResult(ok=False, status=0,
                                      error=f"Network error: {exc}")

        status = resp.status_code
        try:
            body = resp.json()
        except ValueError:
            body = {"raw_text": resp.text or ""}

        if 200 <= status < 300:
            return BookingResult(ok=True, status=status, data=body)

        error_msg = body.get("message") or body.get("error") or resp.reason_phrase
        return BookingResult(ok=False, status=status,
                             error=error_msg, raw=body)