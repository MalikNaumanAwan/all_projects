# app/llm_client.py
import time

# from dotenv import load_dotenv
from typing import List, Dict, Optional, Tuple
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import (
    AIModel,
)  # Assuming AIModel has fields: model_id, provider, category, total_requests, total_response_time, average_response_time

""" load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY") """


# -------------------------------------------------------------------------
# API CALL HELPERS
# -------------------------------------------------------------------------
async def call_groq_api(
    messages: List[Dict[str, str]], model: str, client: AsyncClient, groq_api_key: str
) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "stream": False,
    }
    response = await client.post(url, headers=headers, json=payload)
    response.raise_for_status()
    parsed = response.json()
    return parsed.get("choices", [])[0].get("message", {}).get("content", "")


async def call_mistral_api(
    messages: List[Dict[str, str]],
    model: str,
    client: AsyncClient,
    mistral_api_key: str,
) -> str:
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {mistral_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "stream": False,
    }
    print("provider: MistralAI:", model)
    response = await client.post(url, headers=headers, json=payload)
    response.raise_for_status()
    parsed = response.json()
    return parsed.get("choices", [])[0].get("message", {}).get("content", "")


# -------------------------------------------------------------------------
# DB UPDATE HELPERS
# -------------------------------------------------------------------------
async def update_model_stats(
    db: AsyncSession, model_id: str, response_time: float
) -> None:
    """Update request count and response time metrics for a model."""
    result = await db.execute(select(AIModel).where(AIModel.model_id == model_id))
    model_obj = result.scalar_one_or_none()
    if model_obj:
        model_obj.total_requests = (model_obj.total_requests or 0) + 1
        model_obj.total_response_time = (
            model_obj.total_response_time or 0.0
        ) + response_time
        model_obj.average_response_time = (
            model_obj.total_response_time / model_obj.total_requests
        )
        db.add(model_obj)
        await db.commit()
        await db.refresh(model_obj)


def estimate_complexity(messages: List[Dict[str, str]]) -> float:
    """Return a complexity score between 0 and 1."""
    user_inputs = [m["content"] for m in messages if m["role"] == "user"]
    total_len = sum(len(u.split()) for u in user_inputs)
    if total_len < 20:  # very short/simple
        return 0.1
    elif total_len < 100:
        return 0.5
    else:  # long/complex prompt
        return 0.9


def compute_model_score(model, complexity: float) -> float:
    """
    Compute weighted score for model.
    Higher = better.
    """
    # Normalize rating (assume 1–5 scale)
    rating = (model.rating or 3) / 5.0

    # Normalize latency (invert: lower is better)
    latency = model.average_response_time or float("inf")
    norm_latency = 1 / (1 + latency)  # maps latency -> (0,1]

    # Weight factors (α for rating, β for latency)
    alpha = 0.4 + 0.6 * complexity  # quality matters more if complex
    beta = 1.0 - alpha  # speed matters more if simple

    return (alpha * rating) + (beta * norm_latency)


# -------------------------------------------------------------------------
# MAIN ROUTER
# -------------------------------------------------------------------------
async def get_model_response(
    messages: List[Dict[str, str]],
    model: str,
    category: str,
    db: AsyncSession,
    client: AsyncClient,
    groq_api_key: Optional[str] = None,
    mistral_api_key: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Route request to a model. If requested model fails, or if it belongs to a
    different category, fallback to best available model in requested category.
    Skips providers if their API keys are not provided.
    Returns: (response_text, used_model_id)
    """
    if category in ("vision", "audio"):
        print("MODELS NOT AVAILABLE")
        raise RuntimeError("vision and audio models are not available right now")

    async def normalize_response(m: str, resp: str) -> str:
        """Remove provider prefixes or brackets, normalize whitespace."""
        if isinstance(resp, list):
            resp = " ".join(
                part.get("text", "") for part in resp if part.get("type") == "text"  # type: ignore
            )
        if resp.lower().startswith(m.lower() + ":"):
            resp = resp[len(m) + 1 :].lstrip()
        if resp.startswith(f"[{m}]"):
            resp = resp[len(f"[{m}]") :].lstrip()
        return resp.strip()

    async def try_model(m: str, provider: str) -> Tuple[str, str]:
        """Execute a model call and update stats."""
        print("Routing to:", m, "| Provider:", provider)

        if provider == "groq" and not groq_api_key:
            raise RuntimeError("Skipped Groq: no API key provided")
        if provider == "mistral" and not mistral_api_key:
            raise RuntimeError("Skipped Mistral: no API key provided")

        start = time.perf_counter()
        if provider == "groq":
            raw_resp = await call_groq_api(messages, m, client, groq_api_key)  # type: ignore
        elif provider == "mistral":
            raw_resp = await call_mistral_api(messages, m, client, mistral_api_key)  # type: ignore
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        end = time.perf_counter()

        response_time = end - start
        await update_model_stats(db, m, response_time)

        clean_text = await normalize_response(m, raw_resp)
        return clean_text, m

    # ---------------------------------------------------------------------
    # Fetch requested model
    # ---------------------------------------------------------------------
    result = await db.execute(select(AIModel).where(AIModel.model_id == model))
    requested_model = result.scalar_one_or_none()

    if not requested_model:
        raise ValueError(f"Requested model {model} not found in DB")

    requested_provider = requested_model.provider.lower()
    requested_category = (
        requested_model.category.lower() if requested_model.category else None
    )

    # Skip if provider's key is missing
    if requested_provider == "groq" and not groq_api_key:
        print(f"⚠️ Skipping {model} because Groq API key not provided")
        requested_model = None
    elif requested_provider == "mistral" and not mistral_api_key:
        print(f"⚠️ Skipping {model} because Mistral API key not provided")
        requested_model = None

    # ---------------------------------------------------------------------
    # CASE 1: Try requested model if valid
    # ---------------------------------------------------------------------
    if requested_model and (
        requested_category == category.lower()
        or (category.lower() == "text" and requested_category == "multimodal")
    ):
        try:
            raw, used_model = await try_model(model, requested_provider)
            messages.append({"role": "assistant", "content": raw})
            return raw, used_model
        except Exception as first_err:
            print(f"⚠️ Model {model} failed: {first_err}")

    # ---------------------------------------------------------------------
    # CASE 2: Fallback to category models with valid provider keys
    # ---------------------------------------------------------------------
    result = await db.execute(select(AIModel).where(AIModel.category == category))
    candidates = result.scalars().all()

    # Filter out providers without API keys
    candidates = [
        c
        for c in candidates
        if not (
            (c.provider.lower() == "groq" and not groq_api_key)
            or (c.provider.lower() == "mistral" and not mistral_api_key)
        )
    ]

    if not candidates:
        raise RuntimeError(
            f"No '{category}' model for your API keys. Add another API key or Switch Mode"
        )

    complexity = estimate_complexity(messages)

    candidates_scored = sorted(
        candidates, key=lambda m: compute_model_score(m, complexity), reverse=True
    )

    for candidate in candidates_scored:
        try:
            raw, used_model = await try_model(
                candidate.model_id, candidate.provider.lower()
            )
            messages.append({"role": "assistant", "content": raw})
            return raw, used_model
        except RuntimeError:
            # Re-raise immediately for fatal errors
            raise
        except Exception as err:
            # Only swallow "soft" errors
            print(f"⚠️ Candidate model {candidate.model_id} failed: {err}")

    raise RuntimeError(
        f"All models in category '{category}' failed (after filtering by provider keys)."
    )
