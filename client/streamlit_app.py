"""Simple client‑side Streamlit UI for the chatbot‑demo backend.

Features
--------
* Chat interface powered by the new `st.chat_message` elements.
* Sidebar to configure **API base URL** and optional **Bearer token**.
* Interactive *Booking* form that helps you build a JSON payload that matches the
  `BookingPayload` / `ReschedulePayload` shape used by your Cal.com tools:
  - eventTypeId, booking_uid, start / end (with TZ awareness), title …
  - attendee & responses fields
  Once ready, the form injects the payload into the chat as a Markdown fenced
  JSON block so the agent can decide whether to call `create_booking` or
  `reschedule_booking`.
* Persists chat history across reruns via `st.session_state` so you get a
  seamless back‑and‑forth.

Run with:
    $ streamlit run streamlit_app.py

Make sure your backend is up (default assumes http://localhost:8000/chat) or
change the "API Base URL" in the sidebar.
"""

from __future__ import annotations

import datetime as _dt
import json
from typing import Any, Dict, List

import pytz  # type: ignore
import requests
import streamlit as st

###############################################################################
# Session‑state helpers
###############################################################################

if "messages" not in st.session_state:
    # Each message is a {"role": "user"|"assistant", "content": str}
    st.session_state.messages: List[Dict[str, str]] = []

###############################################################################
# Sidebar ­– configuration & defaults
###############################################################################
USER_EMAIL: str = st.sidebar.text_input("Your email", value="minging234@gmail.com", help="Enter your email address")
st.sidebar.header("Server configuration")
API_BASE_URL: str = st.sidebar.text_input(
    "API Base URL", value="https://chatbot-demo-l7rr.onrender.com", help="Where your FastAPI/LangChain backend lives"
)
CONVERSATION_NAME: str = st.sidebar.text_input(
    "Conversation name", value="web-ui", help="A name for this chat session"
)
# API_KEY: str = st.sidebar.text_input("Bearer token (optional)", type="password")

st.sidebar.markdown("---")

st.sidebar.header("Booking defaults")
DEFAULT_EVENT_TYPE_ID: int = st.sidebar.number_input(
    "eventTypeId", value=2874092, step=1, format="%d"
)
DEFAULT_TZ: str = st.sidebar.text_input("Time zone", value="America/Los_Angeles")

st.sidebar.markdown("---")
st.sidebar.caption("🧪 Built with Streamlit 1.32 + Python 3.11")

###############################################################################
# Page setup
###############################################################################

st.set_page_config(page_title="Chatbot Demo", page_icon="🤖", layout="wide")
st.title("Chatbot Demo ‑ Streamlit UI")


###############################################################################
# Display chat history
###############################################################################

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

###############################################################################
# Chat input
###############################################################################

user_prompt = st.chat_input("Ask something…")
if user_prompt:
    # 1) Add user message locally
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # 2) Build payload for backend
    payload = {
        "message": user_prompt,
        "email": USER_EMAIL,
    }

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "conversation-id": CONVERSATION_NAME,
    }

    # 3) Call backend
    try:
        r = requests.post(
            f"{API_BASE_URL}/chat",
            json=payload,
            headers=headers,
            timeout=30
        )
        r.raise_for_status()
        data = r.json()
        assistant_reply = data.get("reply", "(no 'reply' field in response)")
    except Exception as exc:  # noqa: BLE001
        assistant_reply = f"⚠️ Error talking to backend: {exc}"

    # 4) Render assistant reply
    st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
    st.rerun()
