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
    
    # ---------- new: cancel one booking ----------
    async def cancel_booking(
        self,
        booking_uid: str,
        cancellation_reason: str | None = None,
        all_remaining_bookings: bool = False,
    ) -> dict:
        """
        Cancel a single Cal.com booking (or an entire series if
        ``all_remaining_bookings`` is True).
        """
        url, _ = self._url(f"/bookings/{booking_uid}/cancel", use_v2=True)
        headers = self._auth_headers()
        body: dict[str, Any] = {}
        if cancellation_reason is not None:
            body["cancellationReason"] = cancellation_reason
        if all_remaining_bookings:
            body["allRemainingBookings"] = True

        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=body, headers=headers)
            if r.status_code >= 400:
                try:
                    pprint.pp(r.json())
                except Exception:
                    print(r.text)
                r.raise_for_status()
            return r.json()
        

    # ─────────────────────────────────────────────────────────────
    # NEW: fetch existing bookings for a given invitee e-mail
    # ─────────────────────────────────────────────────────────────
    async def list_bookings(
        self,
        email: str,
        after_start: str | None = None,
        before_end: str | None = None,
        status: str = "upcoming",
    ) -> BookingResult:
        """
        Return every booking whose *invitee* matches `email`, optionally filtered by start/end and status.
        """
        url, params = self._url("/bookings", use_v2=True)
        params["attendeeEmail"] = email
        if not status:
            params["status"] = "upcoming"
        if after_start:
            params["afterStart"] = after_start
        if before_end:
            params["beforeEnd"] = before_end
        headers = self._auth_headers()

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, headers=headers)
            except httpx.RequestError as exc:           # network/DNS failure
                return BookingResult(ok=False, status=0,
                                      error=f"Network error: {exc}")

        status_code = resp.status_code
        try:
            body = resp.json()
        except ValueError:
            body = {"raw_text": resp.text or ""}

        if 200 <= status_code < 300:
            return BookingResult(ok=True, status=status_code, data=body)

        error_msg = (
            body.get("message")          # may be list/dict in v2
            or body.get("error")
            or resp.reason_phrase
        )
        if not isinstance(error_msg, str):
            error_msg = str(error_msg)   # ensure it’s always a str

        return BookingResult(
            ok=False,
            status=status_code,
            error=error_msg,
            raw=body,
        )
    
    # ────────────────────────────────────────────────────────────────
    #  PUBLIC ▸ reschedule = cancel ➊ then create ➋
    # ────────────────────────────────────────────────────────────────
    async def reschedule_booking(
        self,
        old_booking_uid: str,
        new_payload: BookingPayload,
        *,
        cancellation_reason: str | None = "Rescheduled via API",
        all_remaining_bookings: bool = False,
    ) -> BookingResult:
        """
        Finds an existing booking by UID, cancels it, then creates a new one
        with ``new_payload``.  Returns the *new* BookingResult (so callers
        only have to inspect one object).
        """
        # ➊ cancel
        cancel_raw = await self.cancel_booking(
            old_booking_uid,
            cancellation_reason=cancellation_reason,
            all_remaining_bookings=all_remaining_bookings,
        )
        if cancel_raw.get("status") != "success":          # Cal v2 shape
            return BookingResult(
                ok=False,
                status=400,
                error=f"Cancellation failed: {cancel_raw}",
                raw=cancel_raw,
            )

        # ➋ create
        return await self.create_booking(new_payload)
