from typing import Optional, List
from sqlalchemy import Boolean, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from datetime import datetime
import uuid


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    api_keys: Mapped[List["UserApiKey"]] = relationship(
        "UserApiKey", back_populates="user", cascade="all, delete-orphan"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession", back_populates="user"
    )
    is_verified = mapped_column(Boolean, default=False)


class AIModel(Base):
    __tablename__ = "ai_models"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "Groq" / "Mistral"
    model_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )  # API model identifier
    category: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # API model identifier
    rating: Mapped[int] = mapped_column(nullable=False)
    total_requests: Mapped[int] = mapped_column(nullable=True)
    total_response_time: Mapped[float] = mapped_column(nullable=True)
    average_response_time: Mapped[float] = mapped_column(nullable=True)


class UserApiKey(Base):
    __tablename__ = "user_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    api_provider: Mapped[str] = mapped_column(String, nullable=False, index=True)
    api_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="api_keys")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id")
    )
    title: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="Untitled Session"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id")
    )
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    model: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="Untitled Session"
    )
    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages"
    )
