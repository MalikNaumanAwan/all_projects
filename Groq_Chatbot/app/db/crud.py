# app/db/crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.auth.models import ChatMessage
from uuid import UUID


async def save_message(
    db: AsyncSession,
    user_id: UUID,
    session_id: UUID,
    role: str,
    content: str,
    res_model: str,
):
    message = ChatMessage(
        user_id=user_id,
        session_id=session_id,
        role=role,
        content=content,
        model=res_model,
    )
    db.add(message)
    await db.commit()


async def get_recent_messages(db: AsyncSession, user_id: UUID, limit: int = 10):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))
