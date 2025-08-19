import traceback
from pathlib import Path
from typing import List
from uuid import UUID
from fastapi import status
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.auth.authentication import get_current_user
from app.auth.models import AIModel, ChatSession, User, UserApiKey
from app.auth.schemas import (
    ChatPayload,
    ChatSessionOut,
    ChatSessionCreate,
    ChatSessionWithMessages,
    UserApiKeyIn,
    AIModelRead,
    UserApiKeyOut,
)
from app.services.web_search import web_search_serper, build_search_augmented_prompt
from app.db.crud import save_message
from app.db.dependencies import get_db
from app.groq_client import get_model_response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.auth.schemas import ChatMessageOut, ChatSessionDetail, UserChatHistory

router = APIRouter()


# ⛳️ go up 2 levels from chat_router.py → you're now at `app/`
BASE_DIR = Path(__file__).resolve().parent.parent

# 🔍 now locate frontend/static under app/
STATIC_DIR = BASE_DIR / "frontend" / "static"
INDEX_PATH = STATIC_DIR / "index.html"
OCR_PATH = STATIC_DIR / "testocr.html"


@router.get("/", response_class=HTMLResponse)
async def index():
    if not INDEX_PATH.exists():
        raise RuntimeError(f"index.html not found at: {INDEX_PATH}")
    return INDEX_PATH.read_text(encoding="utf-8")


@router.get("/testocr", response_class=HTMLResponse)
async def testocr():
    if not OCR_PATH.exists():
        raise RuntimeError(f"index.html not found at: {OCR_PATH}")
    return OCR_PATH.read_text(encoding="utf-8")


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
        print("payload Category:", payload.category)
        session_id: UUID | None = payload.session_id
        user_message = payload.messages[-1].content

        # Step 1: Create session if needed
        if session_id is None:
            print("Session not received. Creating session...")
            new_session = ChatSession(user_id=user.id)
            db.add(new_session)
            await db.commit()
            await db.refresh(new_session)
            session_id = new_session.id
            print("💡 New session created:", session_id)
            # 🔹 Generate a title using the LLM
            async with AsyncClient(timeout=None) as client:
                title_prompt = f"""
                Create a short, descriptive chat title (max 6 words) for this user query:
                "{payload.messages[-1].content}"

                Rules:
                - No quotes or punctuation at the end
                - Capture the core topic clearly
                - Capitalize each major word
                - Do not include the words 'Title' or 'Chat'
                - Output only the title
                """
                generated_title, _ = await get_model_response(
                    [{"role": "user", "content": title_prompt}],
                    "openai/gpt-oss-20b",
                    "text",
                    db,
                    client,
                )

            # Save title in DB
            new_session.title = generated_title.strip()
            await db.commit()
            print(f"📝 Session title set: {new_session.title}")
        else:
            # Fetch existing session
            result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            existing_session = result.scalar_one_or_none()
            if not existing_session:
                raise HTTPException(status_code=404, detail="Session not found")

            # Increment some counter if you have one (example)
            # existing_session.message_count += 1

            # If title is still default, update it based on latest query
            if existing_session.title.strip().lower() == "new chat session":  # type: ignore
                async with AsyncClient(timeout=None) as client:
                    title_prompt = f"""
                    Create a short, descriptive chat title (max 6 words) for this user query:
                    "{payload.messages[-1].content}"

                    Rules:
                    - No quotes or punctuation at the end
                    - Capture the core topic clearly
                    - Capitalize each major word
                    - Do not include the words 'Title' or 'Chat'
                    - Output only the title
                    """
                    generated_title, _ = await get_model_response(
                        [{"role": "user", "content": title_prompt}],
                        "openai/gpt-oss-20b",
                        "text",
                        db,
                        client,
                    )

                existing_session.title = generated_title.strip()
                await db.commit()
                print(f"📝 Session title updated: {existing_session.title}")
        print("📨 Message received:", user_message)
        print("👤 User ID:", user.id, "| 💬 Session ID:", session_id)
        print("🌐 Web Search Enabled:", getattr(payload, "web_search", False))

        # Step 2: Save user's message
        await save_message(
            db=db,
            user_id=user.id,
            session_id=session_id,
            role="user",
            content=user_message,
            res_model="",
        )

        # Step 3: Fetch previous session messages
        result = await db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        previous_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in sorted(session.messages, key=lambda m: m.created_at)
        ]

        # Step 4: Base system prompt
        messages_for_llm = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that responds in a friendly, approachable, and clear style, similar to ChatGPT."
                    "Follow these formatting rules for all responses:"
                    "- Write all output as a single well-structured GitHub-flavored Markdown block."
                    "- Always start with a descriptive H2 title that includes a relevant emoji."
                    "- Include a short introductory paragraph (1–2 sentences)."
                    "- Organize content into clearly labeled sections using H3 headings."
                    "- Use bullet points or numbered lists for clarity when listing items."
                    "- Provide code examples in fenced code blocks with correct syntax highlighting."
                    "- Use **bold** for important terms and occasional emojis to enhance readability."
                    "- For comparisons or data, use clean Markdown tables."
                    "- Avoid repeating the same content in multiple formats—present only the polished Markdown version."
                    "- Leave one blank line between all sections for readability."
                    "- Explain concepts step-by-step, keeping tone friendly but professional."
                    "- Add a brief summary(if required) or key takeaway(if required) at the end."
                ),
            }
        ] + previous_messages

        # Step 5: Web Search Augmentation with Query Normalization
        if getattr(payload, "web_search", False):
            async with AsyncClient(timeout=None) as client:
                normalization_prompt = f"""
                    Given the conversation so far and the user's latest question, rewrite the question
                    into a highly specific, search-engine-friendly query. Preserve the intent but make it explicit.

                    Conversation Context:
                    {[m['content'] for m in previous_messages]}

                    Latest Question:
                    "{user_message}"

                    Output only the rewritten query, no extra words.no model name.
                    """
                normalized_query = await get_model_response(
                    [{"role": "user", "content": normalization_prompt}],
                    "openai/gpt-oss-20b",
                    "text",
                    db,
                    client,
                )
            normalized_query = normalized_query[0]
            print(f"🔍 Normalized Search Query: {normalized_query}")

            # Step 5b: Call the search API with the normalized query
            search_results = await web_search_serper(normalized_query)

            # Step 5c: Inject search results into the LLM context
            augmented_prompt = build_search_augmented_prompt(
                normalized_query, search_results
            )
            messages_for_llm.append({"role": "system", "content": augmented_prompt})

        # Step 6: Get final LLM response
        # Step 6: Get LLM response
        async with AsyncClient(timeout=None) as client:
            reply_text, used_model = await get_model_response(
                messages_for_llm, payload.model, payload.category, db, client
            )

        # Step 7: Save assistant's response
        await save_message(
            db=db,
            user_id=user.id,
            session_id=session_id,
            role="assistant",
            content=reply_text,
            res_model=used_model,
        )

        print("✅ Sending Response")
        return JSONResponse(
            content={
                "response": reply_text,
                "model": used_model,
                "session_id": str(session_id),
            }
        )

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

    # 🔹 Sort messages by created_at (ascending)
    sorted_messages = sorted(session.messages, key=lambda m: m.created_at)

    # 🔹 Replace with sorted list so response_model gets them in order
    session.messages = sorted_messages
    return session


@router.get("/get_models", response_model=List[AIModelRead])
async def get_models(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),  # ✅ Require login
):
    try:
        result = await db.execute(select(AIModel))
        models = result.scalars().all()
        return models
    except SQLAlchemyError as e:
        print(f"❌ Database error while fetching models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch models from the database.",
        ) from e
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        ) from e


@router.get("/get_api_keys", response_model=UserApiKeyOut)
async def return_api_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserApiKey).where(UserApiKey.user_id == user.id))
    rows = result.scalars().all()

    # Option A: validate from ORM instances (recommended with from_attributes)
    api_keys = [UserApiKeyIn.model_validate(row) for row in rows]

    # Option B: explicit construction (works without from_attributes)
    # api_keys = [UserApiKeyIn(api_provider=row.api_provider, api_key=row.api_key) for row in rows]

    return UserApiKeyOut(api_keys=api_keys)


@router.delete("/delete_api_key")
async def delete_api_key(
    api_key: dict,  # incoming JSON { "api_key": "<value>" }
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key_val = api_key.get("api_key")
    if not key_val:
        raise HTTPException(status_code=400, detail="API key value is required")

    # Delete only if the key belongs to the current user
    stmt = (
        delete(UserApiKey)
        .where(UserApiKey.user_id == user.id)
        .where(UserApiKey.api_key == key_val)
    )
    result = await db.execute(stmt)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="API key not found")

    return {"detail": "API key deleted successfully"}


""" from fastapi import APIRouter, UploadFile, File
import httpx
import base64
import mimetypes
import os
from dotenv import load_dotenv

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_URL = "https://api.mistral.ai/v1/ocr"


def load_image_file(file: UploadFile):
    mime_type, _ = mimetypes.guess_type(file.filename)
    content = file.file.read()
    encoded = base64.b64encode(content).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


@router.post("/chat/ocr")
async def chat_ocr(file: UploadFile = File(...)):
    try:
        base64_url = load_image_file(file)

        payload = {
            "model": "mistral-ocr-latest",
            "document": {"type": "image_url", "image_url": base64_url},
        }

        async with httpx.AsyncClient(timeout=None) as client:
            resp = await client.post(
                MISTRAL_URL,
                headers={
                    "Authorization": f"Bearer {MISTRAL_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        resp.raise_for_status()
        result = resp.json()
        extracted_text = result.get("text", "")
        return JSONResponse({"text": extracted_text})

    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500) """
