# app/llm_client.py
import os
import time
from dotenv import load_dotenv
from typing import List, Dict, Tuple
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import (
    AIModel,
)  # Assuming AIModel has fields: model_id, provider, category, total_requests, total_response_time, average_response_time

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


# -------------------------------------------------------------------------
# API CALL HELPERS
# -------------------------------------------------------------------------
async def call_groq_api(
    messages: List[Dict[str, str]], model: str, client: AsyncClient
) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
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
    messages: List[Dict[str, str]], model: str, client: AsyncClient
) -> str:
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
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


# -------------------------------------------------------------------------
# MAIN ROUTER
# -------------------------------------------------------------------------
async def get_model_response(
    messages: List[Dict[str, str]],
    model: str,
    category: str,
    db: AsyncSession,
    client: AsyncClient,
) -> Tuple[str, str]:
    """
    Route request to a model. If requested model fails, or if it belongs to a
    different category, fallback to best available model in requested category.
    Returns: (response_text, used_model_id)
    """

    async def normalize_response(m: str, resp: str) -> str:
        """Remove provider prefixes or brackets, normalize whitespace."""
        if isinstance(resp, list):
            resp = " ".join(
                part.get("text", "") for part in resp if part.get("type") == "text"
            )
        if resp.lower().startswith(m.lower() + ":"):
            resp = resp[len(m) + 1 :].lstrip()
        if resp.startswith(f"[{m}]"):
            resp = resp[len(f"[{m}]") :].lstrip()
        return resp.strip()

    async def try_model(m: str, provider: str) -> Tuple[str, str]:
        """Execute a model call and update stats."""
        print("Routing to:", m, "| Provider:", provider)

        start = time.perf_counter()
        if provider == "groq":
            raw_resp = await call_groq_api(messages, m, client)
        elif provider == "mistral":
            raw_resp = await call_mistral_api(messages, m, client)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        end = time.perf_counter()

        response_time = end - start
        await update_model_stats(db, m, response_time)

        clean_text = await normalize_response(m, raw_resp)
        return clean_text, m

    # ---------------------------------------------------------------------
    # Fetch model info
    # ---------------------------------------------------------------------
    result = await db.execute(select(AIModel).where(AIModel.model_id == model))
    requested_model = result.scalar_one_or_none()

    if not requested_model:
        raise ValueError(f"Requested model {model} not found in DB")

    requested_provider = requested_model.provider.lower()
    requested_category = (
        requested_model.category.lower() if requested_model.category else None
    )

    # ---------------------------------------------------------------------
    # CASE 1: Requested model's category matches the requested category
    # ---------------------------------------------------------------------

    if requested_category == category.lower() or (
        category.lower() == "text" and requested_category == "multimodal"
    ):
        try:
            raw, used_model = await try_model(model, requested_provider)
            messages.append({"role": "assistant", "content": raw})
            return raw, used_model
        except Exception as first_err:
            print(f"⚠️ Model {model} failed: {first_err}")

    else:
        print(
            f"⚠️ Requested model {model} belongs to category '{requested_category}', "
            f"but user requested category '{category}'. Skipping to category-based selection."
        )
    # ---------------------------------------------------------------------
    # CASE 2: Fallback — pick best model in requested category
    # ---------------------------------------------------------------------
    result = await db.execute(select(AIModel).where(AIModel.category == category))
    candidates = result.scalars().all()

    if not candidates:
        raise RuntimeError(f"No models available in category '{category}'")

    # sort by average_response_time ascending (fastest first)
    candidates_sorted = sorted(
        candidates, key=lambda m: (m.average_response_time or float("inf"))
    )

    for candidate in candidates_sorted:
        try:
            raw, used_model = await try_model(
                candidate.model_id, candidate.provider.lower()
            )
            messages.append({"role": "assistant", "content": raw})
            return raw, used_model
        except Exception as err:
            print(f"⚠️ Candidate model {candidate.model_id} failed: {err}")

    raise RuntimeError(
        f"All models in category '{category}' failed to produce a response."
    )
