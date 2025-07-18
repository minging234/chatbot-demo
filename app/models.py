
from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = Field(None, description="Client session id")
    email: str
    message: str

class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
