import traceback
from pathlib import Path
from uuid import UUID
from fastapi import status
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.auth.authentication import get_current_user
from app.auth.models import ChatSession, User, UserApiKey
from app.auth.schemas import (
    ChatPayload,
    ChatSessionOut,
    ChatSessionCreate,
    ChatSessionWithMessages,
    UserApiKeyIn,
)
from app.db.crud import save_message
from app.db.dependencies import get_db
from app.groq_client import get_groq_response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.auth.schemas import ChatMessageOut, ChatSessionDetail, UserChatHistory

router = APIRouter()


# ⛳️ go up 2 levels from chat_router.py → you're now at `app/`
BASE_DIR = Path(__file__).resolve().parent.parent

# 🔍 now locate frontend/static under app/
STATIC_DIR = BASE_DIR / "frontend" / "static"
INDEX_PATH = STATIC_DIR / "index.html"


@router.get("/", response_class=HTMLResponse)
async def index():
    if not INDEX_PATH.exists():
        raise RuntimeError(f"index.html not found at: {INDEX_PATH}")
    return INDEX_PATH.read_text(encoding="utf-8")


@router.post("/save_api_key")
async def save_api_key(
    payload: UserApiKeyIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        new_key = UserApiKey(
            user_id=user.id,
            api_provider=payload.api_provider,
            api_key=payload.api_key,
        )
        db.add(new_key)
        await db.commit()
        return JSONResponse(content={"success": "API key added successfully"})
    except IntegrityError:
        await db.rollback()
        # Likely duplicate api_key violation
        return JSONResponse(
            content={"detail": "API key already exists."},
            status_code=400,
        )
    except Exception:
        await db.rollback()
        print("❌ Exception occurred during /save_api_key:")
        traceback.print_exc()
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)


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

        # Step 1: If no session_id, create a new one
        if session_id is None:
            print("Session not received. Creating session...")
            new_session = ChatSession(user_id=user.id)
            db.add(new_session)
            await db.commit()
            await db.refresh(new_session)
            session_id = new_session.id
            print("💡 New session created:", session_id)

        print("📨 Message received:", user_message)
        print("👤 User ID:", user.id, "| 💬 Session ID:", session_id)

        # Step 2: Save the new user's message
        await save_message(
            db=db,
            user_id=user.id,
            session_id=session_id,
            role="user",
            content=user_message,
        )

        # Step 3: Fetch all previous messages for this session
        result = await db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Convert DB messages to dict format for LLM
        previous_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in sorted(session.messages, key=lambda m: m.created_at)
        ]

        # Step 4: Add system prompt at the start
        messages_for_llm = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that responds in a friendly, approachable, and clear style, "
                    "similar to ChatGPT. Use GitHub-flavored markdown with headings, bullet points, and code blocks, "
                    "but ensure your responses are well-spaced with paragraphs and line breaks to avoid congestion.\n\n"
                    "Write your replies in natural, conversational English. Introduce concepts gently, "
                    "explain ideas step-by-step, and use examples where helpful. "
                    "Keep the tone warm and encouraging, like a knowledgeable peer.\n\n"
                    "Avoid large blocks of text without breaks. Use lists or sections to organize information clearly. "
                    "When appropriate, add friendly greetings or closing remarks to make the interaction engaging."
                ),
            },
        ] + previous_messages

        # Step 5: Call LLM with complete conversation
        async with AsyncClient(timeout=None) as client:
            reply = await get_groq_response(messages_for_llm, payload.model, client)

        # Step 6: Save assistant's response
        await save_message(
            db=db,
            user_id=user.id,
            session_id=session_id,
            role="assistant",
            content=reply,
        )

        print("✅ Sending Response")
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
        return UserChatHistory(user_id=user.id, sessions=session_details)

    except Exception as e:
        print("❌ Error fetching sessions:", e)
        traceback.print_exc()
        return JSONResponse(
            content={"error": "Could not retrieve session history"}, status_code=500
        )


@router.delete(
    "/chat/delete_session/{session_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_chat_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    print("DELETING CHAT SESSION")
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user.id
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    await db.commit()
    return


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
