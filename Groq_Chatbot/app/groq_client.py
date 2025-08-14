# app/llm_client.py
import os
import random
from dotenv import load_dotenv
from typing import List, Dict
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import AIModel  # Assuming you have a Model table

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


async def get_model_provider_from_db(model_id: str, db: AsyncSession) -> str:
    """Fetch the provider for a given model_id from DB."""
    result = await db.execute(
        select(AIModel.provider).where(AIModel.model_id == model_id)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise ValueError(f"Provider not found for model: {model_id}")
    return provider.lower()


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


async def get_model_response(
    messages: List[Dict[str, str]],
    model: str,
    db: AsyncSession,
    client: AsyncClient,
) -> tuple[str, str]:  # ✅ Return (reply_text, model_name)

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

    async def try_model(m: str) -> tuple[str, str]:
        """Try a single model and return (clean_text, model_id)."""
        print("Routing to:", m)
        result = await db.execute(select(AIModel.provider).where(AIModel.model_id == m))
        providers = [p.lower() for (p,) in result.all()]
        if not providers:
            raise ValueError(f"Provider not found for model: {m}")

        provider = random.choice(providers)

        if provider == "groq":
            raw_resp = await call_groq_api(messages, m, client)
        elif provider == "mistral":
            raw_resp = await call_mistral_api(messages, m, client)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        clean_text = await normalize_response(m, raw_resp)
        return clean_text, m  # ✅ Keep model separate

    # Try primary model
    try:
        raw, used_model = await try_model(model)
        messages.append({"role": "assistant", "content": raw})
        return raw, used_model
    except Exception as first_err:
        print(f"⚠️ Model {model} failed: {first_err}")

    # Try fallbacks
    result = await db.execute(select(AIModel.model_id))
    all_models = [mid for (mid,) in result.all() if mid != model]

    for fallback_model in all_models:
        try:
            raw, used_model = await try_model(fallback_model)
            messages.append({"role": "assistant", "content": raw})
            return raw, used_model
        except Exception as err:
            print(f"⚠️ Fallback model {fallback_model} failed: {err}")

    raise RuntimeError("All models failed to produce a response.")
