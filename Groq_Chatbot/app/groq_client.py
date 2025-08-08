# app/groq_client.py
import os
from dotenv import load_dotenv
from typing import List, Dict
from httpx import AsyncClient

import re

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
# TTS_MODEL = "playai-tts"


def fix_common_spacing_issues(text: str) -> str:
    replacements = [
        (r"\bGro q\b", "Groq"),
        (r"\bcompound -beta\b", "compound-beta"),
        (r"\bCompound -Beta\b", "Compound-Beta"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    return text


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
    parsed = response.json()

    content = parsed.get("choices", [])[0].get("message", {}).get("content", "")
    return content
