# app/groq_client.py
import os
from dotenv import load_dotenv
from typing import List, Dict
from httpx import AsyncClient


load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # Ensure .env uses GROQ_API_KEY

VALID_MODELS = {
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "allam-2-7b",
    "compound-beta",
    "compound-beta-mini",
    "deepseek-r1-distill-llama-70b",
    "gemma2-9b-it",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-guard-4-12b",
    "meta-llama/llama-prompt-guard-2-22m",
    "meta-llama/llama-prompt-guard-2-86m",
    "moonshotai/kimi-k2-instruct",
    "qwen/qwen3-32b",
}


async def get_groq_response(
    messages: List[Dict[str, str]], model: str, client: AsyncClient
) -> str:
    if model not in VALID_MODELS:
        raise ValueError(f"Invalid model selected: {model}")

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
    model_info = {
        "region": response.headers.get("x-groq-region"),
        "requests_limit": response.headers.get("x-ratelimit-limit-requests"),
        "tokens_limit": response.headers.get("x-ratelimit-limit-tokens"),
        "requests_remaining": response.headers.get("x-ratelimit-remaining-requests"),
        "tokens_remaining": response.headers.get("x-ratelimit-remaining-tokens"),
        "requests_reset_in": response.headers.get("x-ratelimit-reset-requests"),
        "tokens_reset_in": response.headers.get("x-ratelimit-reset-tokens"),
        "request_id": response.headers.get("x-request-id"),
    }
    print("📊 Groq Model: ", model)
    for k, v in model_info.items():
        print(f"{k}: {v}")
    parsed = response.json()
    content = parsed.get("choices", [])[0].get("message", {}).get("content", "")
    return content
