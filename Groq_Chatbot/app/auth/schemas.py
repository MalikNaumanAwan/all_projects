from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: EmailStr

    class Config:
        from_attributes = True  # for SQLAlchemy <-> Pydantic mapping


class Message(BaseModel):
    role: str
    content: str


class UserApiKeyIn(BaseModel):
    api_provider: str
    api_key: str


class ChatPayload(BaseModel):
    session_id: UUID | None = None
    messages: List[Message]
    model: str
    web_search: bool = False


class ChatRequest(BaseModel):
    session_id: UUID | None = None
    user_id: UUID
    message: str
    model: str


class ChatSessionCreate(BaseModel):
    user_id: UUID
    title: Optional[str] = None


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: Optional[str]
    created_at: datetime


# ----- Optionally: nested messages under a session -----


# ---- MESSAGE ----
class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID | None = None
    user_id: UUID
    role: str
    content: str
    created_at: datetime
    model: str


class ChatSessionWithMessages(BaseModel):
    id: UUID
    title: Optional[str]
    messages: List[ChatMessageOut]


# ---- SESSION + MESSAGES ----
class ChatSessionDetail(ChatSessionOut):
    messages: List[ChatMessageOut]


# ----- Final Nesting: Full User Chat History -----


class UserChatHistory(BaseModel):
    user_id: UUID
    sessions: List[ChatSessionDetail]


# ----- Chat Message Schemas -----


class ChatMessageSchema(BaseModel):
    user_id: UUID
    session_id: UUID | None = None
    role: str
    content: str


class AIModelBase(BaseModel):
    provider: str
    model_id: str


class AIModelCreate(AIModelBase):
    pass


class AIModelRead(AIModelBase):
    id: int

    model_config = {
        "from_attributes": True  # Enables reading directly from SQLAlchemy objects
    }
