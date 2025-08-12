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
) -> str:
    print("DEBUG:", model, type(model))
    result = await db.execute(select(AIModel.provider).where(AIModel.model_id == model))
    providers = [p.lower() for (p,) in result.all()]  # unpack directly
    if not providers:
        raise ValueError(f"Provider not found for model: {model}")

    provider = random.choice(providers)  # safe now

    if provider == "groq":
        return await call_groq_api(messages, model, client)
    elif provider == "mistral":
        return await call_mistral_api(messages, model, client)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
