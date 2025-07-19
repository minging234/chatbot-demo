
from fastapi import FastAPI, Depends, Header
from .models import ChatRequest, ChatResponse
from .di import orchestrator, conversation_id_header, enforce_rate_limit, lifespan
from .orchestrator import ChatOrchestrator
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the project root directory
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(lifespan=lifespan)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    cid: str = Depends(conversation_id_header),
    orch: ChatOrchestrator = Depends(orchestrator),
    enforce_rate_limit_result=Depends(enforce_rate_limit)
):
    reply, cid = await orch.handle(req.message, cid, req.email)
    return ChatResponse(conversation_id=cid, reply=reply)


"""
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "conversation-id: my-convo-id" \
  -d '{
    "message": "Oh, her email grace2@example.com, my name is jimmy, email is minging234@gmail.com, use default for all the others. can you help with that?",
    "email": "test@example.com"
  }'

"Hello, who won the world cup in 2018?",
"help me book a meeting next monday at 10 am with Grace"
"her email grace2@example.com, my name is jimmy, email is minging234@gmail.com, use default for all the others. can you help with that?",
"Oh, her email grace2@example.com, my name is jimmy, email is "
"minging234@gmail.com, use default for all the others. can you help with that?"
"""


if __name__ == "__main__":
    import requests

    API_URL = "http://localhost:8000/chat"
    CONVERSATION_ID = "my-convo-id"

    payload = {
        "message": (
            # "confirmed, help me book it"
            # "can you help book another time at 10am pst next monday?"
            # "help me book a meeting next monday 07/21 at 10 am with Grace"
            # "for the response, her name is Alice and email alice@example.com use default for all the others. can you help with that?"
            # "Oh, her email grace2@example.com, my name is jimmy, email is "
            # "minging234@gmail.com, use default for all the others. can you help with that?"
            "List all the upcoming meeting with Alice, here email is alice@example.com"
        ),
        "email": "test@example.com",
    }

    headers = {
        "Content-Type": "application/json",
        "conversation-id": CONVERSATION_ID,
    }

    response = requests.post(API_URL, json=payload, headers=headers, timeout=10)
    print(payload["message"])
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())