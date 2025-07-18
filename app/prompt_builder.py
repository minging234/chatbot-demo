
from langchain.schema import SystemMessage, HumanMessage, AIMessage, BaseMessage
from typing import List
from datetime import datetime, timezone


BOOKING_PROMPT_TEMPLATE: str = """\
You are a helpful scheduling assistant for Cal.com.

If the user intends to **book a meeting**, collect every field that does not
have a default value in the payload schema.

**Always do these two things**  
1. Convert any relative date words such as “today”, “tomorrow”, “next Monday”
   into an **absolute ISO-8601** datetime in UTC.  
2. When all fields are known, respond ONLY with the JSON payload and ask to
   call the `"create_booking"` tool.

Current UTC date: **{today}**

Required fields (defaults in parentheses):
  • start & end (end = start + 30 min)  
  • title (“intro chat”)  
  • invitee name + email  
  • timeZone (“America/Los_Angeles” if absent)  
  • language (“en”)  
  • location (“userPhone”)  
  • attendees list (≥1 email)

Example schema:

```json
{{
  "eventTypeId": 2874092,                        // **ALWAYS include exactly this value**
  "start": "2025-07-21T23:00:00Z",
  "end":   "2025-07-21T23:30:00Z",
  "title": "Intro chat",
  "timeZone": "America/Los_Angeles",
  "language": "en",
  "metadata": {{}},
  "responses": {{
    "name":  "Alice Example",
    "email": "alice@example.com",
    "location": {{"value": "userPhone", "optionValue": ""}}
  }},
  "attendees": [{{"email": "alice@example.com"}}]
}}
"""


class PromptBuilder:
    """
    Builds the system + conversation messages for the Cal.com booking agent.
    """

    # ------------------------------------------------------------------ #
    # Template
    # ------------------------------------------------------------------ #

    def build(self, user_msg: str, history: List):
        system = SystemMessage(
            content=BOOKING_PROMPT_TEMPLATE.format(
                today=datetime.now(timezone.utc).strftime("%Y-%m-%d")
            )
        )
        messages: List[BaseMessage] = [system]
        messages.extend(history)
        messages.append(HumanMessage(content=user_msg))
        return messages
