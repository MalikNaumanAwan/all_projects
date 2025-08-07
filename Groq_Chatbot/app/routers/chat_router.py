from fastapi import APIRouter, Depends
from app.auth.schemas import ChatPayload
from app.auth.models import User
from fastapi.responses import StreamingResponse, HTMLResponse
from app.groq_client import stream_groq_response
from httpx import AsyncClient
from pathlib import Path
from app.auth.authentication import get_current_user

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
    payload: ChatPayload, user: User = Depends(get_current_user)
):
    async def event_stream():
        async with AsyncClient(timeout=None) as client:
            try:
                # Convert List[Message] → List[Dict[str, str]]
                message_dicts = [
                    {
                        "role": "system",
                        "content": "Respond in GitHub-flavored markdown. Use headings, bullet points, and code blocks where needed.",
                    }
                ] + [m.model_dump() for m in payload.messages]

                async for token in stream_groq_response(
                    message_dicts, payload.model, client
                ):
                    yield f"data: {token}\n\n"

                yield "data: [DONE]\n\n"

            except Exception as e:
                yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
