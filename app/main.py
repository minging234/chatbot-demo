
from fastapi import FastAPI, Depends, Header
from .models import ChatRequest, ChatResponse
from .di import orchestrator, conversation_id_header
from .orchestrator import ChatOrchestrator
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the project root directory
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

app = FastAPI()

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest,
                        cid: str = Depends(conversation_id_header),
                        orch: ChatOrchestrator = Depends(orchestrator)):
    reply, cid = await orch.handle(req.message, cid, req.email)
    return ChatResponse(conversation_id=cid, reply=reply)


"""
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "conversation-id: my-convo-id" \
  -d '{
    "message": "Hello, who won the world cup in 2018?",
    "email": "test@example.com"
  }'
"""
