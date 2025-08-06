from typing import List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


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


class ChatPayload(BaseModel):
    messages: List[Message]
    model: str
