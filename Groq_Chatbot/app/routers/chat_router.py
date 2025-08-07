import traceback
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.auth.authentication import get_current_user
from app.auth.models import ChatSession, User
from app.auth.schemas import (
    ChatPayload,
    ChatSessionOut,
    ChatSessionCreate,
    ChatSessionWithMessages,
)
from app.db.crud import save_message
from app.db.dependencies import get_db
from app.groq_client import get_groq_response
from sqlalchemy import select

from app.auth.schemas import ChatMessageOut, ChatSessionDetail, UserChatHistory

router = APIRouter()


# ⛳️ go up 2 levels from chat_router.py → you're now at `app/`
BASE_DIR = Path(__file__).resolve().parent.parent

# 🔍 now locate frontend/static under app/
STATIC_DIR = BASE_DIR / "frontend" / "static"
INDEX_PATH = STATIC_DIR / "index.html"


@router.get("/", response_class=HTMLResponse)
async def index():
    print("Serving Index at:", INDEX_PATH)
    if not INDEX_PATH.exists():
        raise RuntimeError(f"index.html not found at: {INDEX_PATH}")
    return INDEX_PATH.read_text(encoding="utf-8")


@router.post("/chat")
async def chat_without_tts(
    payload: ChatPayload,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        print("payload session id:", payload.session_id)
        session_id: UUID | None = payload.session_id
        user_message = payload.messages[-1].content

        # Step 1: If session_id not provided, create a new chat session
        if session_id is None:
            print("Session not recieved. creating session")
            print("user_id", user.id)
            new_session = ChatSession(user_id=user.id)
            db.add(new_session)
            await db.commit()
            await db.refresh(new_session)
            session_id = new_session.id
            print("💡 New session created:", session_id)

        print("📨 Message received:", user_message)
        print("👤 User ID:", user.id, "| 💬 Session ID:", session_id)

        # Step 2: Save user's message
        await save_message(
            db=db,
            user_id=user.id,
            session_id=session_id,
            role="user",
            content=user_message,
        )

        # Step 3: Build context
        messages = [
            {
                "role": "system",
                "content": (
                    "Respond in GitHub-flavored markdown. "
                    "Use headings, bullet points, and code blocks where needed."
                ),
            }
        ] + [m.model_dump() for m in payload.messages]

        # Step 4: Get assistant reply from Groq
        async with AsyncClient(timeout=None) as client:
            reply = await get_groq_response(messages, payload.model, client)

        # Step 5: Save assistant's response
        await save_message(
            db=db,
            user_id=user.id,
            session_id=session_id,
            role="assistant",
            content=reply,
        )
        print("Sending Response")
        return JSONResponse(content={"response": reply, "session_id": str(session_id)})

    except Exception as e:
        print("❌ Exception occurred during /chat:")
        traceback.print_exc()
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/get_sessions", response_model=UserChatHistory)
async def get_user_sessions_with_messages(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        # ⚙️ Load sessions + related messages in one efficient query
        result = await db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.user_id == user.id)
            .order_by(ChatSession.created_at.desc())
        )
        sessions = result.scalars().all()

        session_details = []
        for session in sessions:
            messages = [
                ChatMessageOut.model_validate(message)
                for message in sorted(session.messages, key=lambda m: m.created_at)
            ]
            session_details.append(
                ChatSessionDetail(
                    id=session.id,
                    user_id=session.user_id,
                    title=session.title,
                    created_at=session.created_at,
                    messages=messages,
                )  # type: ignore
            )
        print("session_details index 0: ", session_details[0])
        return UserChatHistory(user_id=user.id, sessions=session_details)

    except Exception as e:
        print("❌ Error fetching sessions:", e)
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Could not retrieve session history"}, status_code=500
        )


# FastAPI route
@router.post("/chat/session", response_model=ChatSessionOut)
async def create_chat_session(
    session_data: ChatSessionCreate, db: AsyncSession = Depends(get_db)
):
    print("getting session")
    new_session = ChatSession(
        user_id=session_data.user_id, title=session_data.title  # optional
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session


@router.get("/profile")
async def get_user_profile(user: User = Depends(get_current_user)):
    return {"id": user.id}


@router.get(
    "/chat/session/{session_id}/messages",
    response_model=ChatSessionWithMessages,
)
async def get_session_messages(session_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session  # ✅ messages now loaded eagerly
