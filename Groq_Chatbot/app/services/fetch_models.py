import os
import json
import time
import math
import asyncio
from time import sleep
from typing import Dict, Any, List, Optional, Tuple

import requests
import pandas as pd
import httpx

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ===== Your app imports (unchanged) =====
from app.db.dependencies import get_db
from app.auth.models import AIModel


# =========================
# Load environment variables
# =========================
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is required.")
if not MISTRAL_API_KEY:
    raise RuntimeError("MISTRAL_API_KEY is required.")
if not SERPER_API_KEY:
    # Not fatal, but strongly recommended. We'll proceed with blank snippets.
    print("⚠️  SERPER_API_KEY not found; model descriptions will default to minimal.")

# =========================
# Provider Endpoints
# =========================
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

MISTRAL_MODELS_URL = "https://api.mistral.ai/v1/models"
MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"

SERPER_SEARCH_URL = "https://google.serper.dev/search"


# =========================
# Fetch models from providers
# =========================
def get_models_from_groq() -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    r = requests.get(GROQ_MODELS_URL, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])


def get_models_from_mistral() -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}"}
    r = requests.get(MISTRAL_MODELS_URL, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])


def collect_all_models() -> List[Dict[str, str]]:
    all_models: List[Dict[str, str]] = []
    for model in get_models_from_groq():
        mid = model.get("id") or model.get("name") or ""
        if mid:
            all_models.append({"provider": "Groq", "model_id": mid})

    for model in get_models_from_mistral():
        mid = model.get("id") or model.get("name") or ""
        if mid:
            all_models.append({"provider": "Mistral", "model_id": mid})

    # Deduplicate just in case (provider+model_id)
    seen = set()
    unique: List[Dict[str, str]] = []
    for m in all_models:
        key = (m["provider"], m["model_id"])
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique


# =========================
# Fetch real-time info from Serper
# =========================
def search_model_info(model_id: str) -> str:
    if not SERPER_API_KEY:
        return "No description available."

    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": model_id}
    try:
        response = requests.post(
            SERPER_SEARCH_URL, json=payload, headers=headers, timeout=20
        )
        response.raise_for_status()
        data = response.json()
        snippet = data.get("answer_box", {}).get("snippet")
        if snippet:
            return snippet
        org = data.get("organic") or []
        if org:
            return org[0].get("snippet", "No description available.")
        return "No description available."
    except Exception as e:
        print(f"Error fetching info for {model_id}: {e}")
        return "No description available."


# =========================
# Categorize & Rate models using Groq REST API (async)
# =========================
CATEGORIZER_MODEL = "openai/gpt-oss-120b"  # keep as-is unless you want to tune


async def categorize_models(models: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Returns: list of {provider, model_id, category, rating}
    """
    out: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=40) as client:
        for model in models:
            model_id = model.get("model_id", "unknown").strip()
            provider = model.get("provider", "unknown")
            try:
                print(f"🔎 Categorizing: {provider} | {model_id}")
                description = search_model_info(model_id)

                messages = [
                    {
                        "role": "user",
                        "content": f"""
You are an AI model evaluator.
Based on this description, classify the model into a SINGLE-WORD category
(one of: coding, text, vision, audio, multimodal).
Also, rate the model performance considering its category on a scale of 1–10, where:
10 = state-of-the-art,
7–9 = strong performer,
4–6 = average,
1–3 = weak/obsolete.

Respond in strict JSON with keys: category, rating.

Model ID: {model_id}
Description: {description}
""".strip(),
                    }
                ]

                payload = {
                    "model": CATEGORIZER_MODEL,
                    "messages": messages,
                    "temperature": 0,
                    "stream": False,
                }
                resp = await client.post(
                    GROQ_CHAT_URL,
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()

                try:
                    parsed = json.loads(content)
                    category = str(parsed.get("category", "unknown")).lower().strip()
                    rating = parsed.get("rating", "unknown")
                    # normalize rating to int if possible
                    rating = (
                        int(rating)
                        if isinstance(rating, (int, float, str))
                        and str(rating).isdigit()
                        else rating
                    )
                except Exception:
                    category, rating = "unknown", "unknown"

                print(f"   → category={category} rating={rating}")
                out.append(
                    {
                        "provider": provider,
                        "model_id": model_id,
                        "category": category,
                        "rating": rating,
                    }
                )
                sleep(0.9)  # polite pacing
            except Exception as e:
                print(f"Error categorizing model {provider}:{model_id}: {e}")
                out.append(
                    {
                        "provider": provider,
                        "model_id": model_id,
                        "category": "unknown",
                        "rating": "unknown",
                    }
                )
    return out


# =========================
# Ping (chat "hi") eligible models
# =========================
ELIGIBLE_CATEGORIES = {"text", "coding", "multimodal"}


class RateLimiter:
    """Simple async token bucket using a semaphore."""

    def __init__(self, concurrency: int = 4):
        self.sem = asyncio.Semaphore(concurrency)

    async def __aenter__(self):
        await self.sem.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.sem.release()


async def _retry_async(fn, retries: int = 2, backoff: float = 1.5):
    last_exc = None
    for i in range(retries + 1):
        try:
            return await fn()
        except Exception as e:
            last_exc = e
            if i < retries:
                await asyncio.sleep(backoff**i)
    raise last_exc  # type: ignore


async def _ping_groq_model(
    client: httpx.AsyncClient, model_id: str
) -> Tuple[bool, float, Optional[str]]:
    async def _do():
        start = time.monotonic()
        resp = await client.post(
            GROQ_CHAT_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": "hi"}],
                "temperature": 0,
                "stream": False,
            },
        )
        elapsed = time.monotonic() - start
        ok = resp.status_code == 200
        err = None if ok else f"HTTP {resp.status_code}: {resp.text[:200]}"
        return ok, elapsed, err

    return await _retry_async(_do)


async def _ping_mistral_model(
    client: httpx.AsyncClient, model_id: str
) -> Tuple[bool, float, Optional[str]]:
    async def _do():
        start = time.monotonic()
        resp = await client.post(
            MISTRAL_CHAT_URL,
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": "hi"}],
                "temperature": 0,
                "stream": False,
            },
        )
        elapsed = time.monotonic() - start
        ok = resp.status_code == 200
        err = None if ok else f"HTTP {resp.status_code}: {resp.text[:200]}"
        return ok, elapsed, err

    return await _retry_async(_do)


async def ping_models(models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Input models must already include category & rating.
    Returns ping results list with fields:
      provider, model_id, category, rating, ping_ok, latency_sec, error
    """
    limiter = RateLimiter(concurrency=4)
    results: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=60) as client:
        tasks = []
        for m in models:
            provider = m["provider"]
            model_id = m["model_id"]
            category = (m.get("category") or "").lower()
            rating = m.get("rating")

            if category not in ELIGIBLE_CATEGORIES:
                continue

            async def _task(p=provider, mid=model_id, cat=category, rat=rating):
                async with limiter:
                    try:
                        if p == "Groq":
                            ok, latency, err = await _ping_groq_model(client, mid)
                        elif p == "Mistral":
                            ok, latency, err = await _ping_mistral_model(client, mid)
                        else:
                            ok, latency, err = (
                                False,
                                math.nan,
                                f"Unsupported provider {p}",
                            )
                        results.append(
                            {
                                "provider": p,
                                "model_id": mid,
                                "category": cat,
                                "rating": rat,
                                "ping_ok": ok,
                                "latency_sec": (
                                    round(latency, 3)
                                    if isinstance(latency, float)
                                    else latency
                                ),
                                "error": err,
                            }
                        )
                    except Exception as e:
                        results.append(
                            {
                                "provider": p,
                                "model_id": mid,
                                "category": cat,
                                "rating": rat,
                                "ping_ok": False,
                                "latency_sec": math.nan,
                                "error": str(e)[:200],
                            }
                        )

            tasks.append(asyncio.create_task(_task()))

        if tasks:
            await asyncio.gather(*tasks)
    return results


# =========================
# Save to DB & Excel (models + pings)
# =========================
async def persist_models_to_db(categorized: List[Dict[str, Any]]) -> bool:
    wrote_to_db = False
    try:
        async for db in get_db():  # works when app is running
            assert isinstance(db, AsyncSession)
            for m in categorized:
                try:
                    result = await db.execute(
                        select(AIModel).where(AIModel.model_id == m["model_id"])
                    )
                    row = result.scalar_one_or_none()
                    if row is None:
                        db.add(
                            AIModel(
                                provider=m["provider"],
                                model_id=m["model_id"],
                                category=m.get("category"),
                                rating=m.get("rating"),
                                total_requests=0,
                                total_response_time=0.0,
                                average_response_time=0.0,
                            )
                        )
                    else:
                        # keep provider/model_id stable; update category/rating if changed
                        row.category = m.get("category") or row.category
                        row.rating = m.get("rating") or row.rating
                except Exception as e:
                    await db.rollback()
                    print(f"⚠️ Failed to upsert {m['model_id']}: {e}")
            await db.commit()
            wrote_to_db = True
    except Exception as e:
        print("⚠️ Could not write models to DB via get_db(). Is FastAPI running?", e)
    return wrote_to_db


async def persist_pings_to_db(pings: List[Dict[str, Any]]) -> bool:
    wrote = False
    try:
        async for db in get_db():
            assert isinstance(db, AsyncSession)
            for p in pings:
                try:
                    # Update requests/response_time/average_response_time
                    result = await db.execute(
                        select(AIModel).where(AIModel.model_id == p["model_id"])
                    )
                    row = result.scalar_one_or_none()
                    if row:
                        row.total_requests = (row.total_requests or 0) + 1
                        if (
                            p["ping_ok"]
                            and isinstance(p["latency_sec"], (int, float))
                            and not math.isnan(p["latency_sec"])
                        ):
                            row.total_response_time = float(p["latency_sec"])
                            # Recompute a simple rolling average
                            # avg_{n} = avg_{n-1} + (x_n - avg_{n-1})/n
                            n = max(row.total_requests, 1)
                            prev_avg = float(row.average_response_time or 0.0)
                            new_val = float(p["latency_sec"])
                            row.average_response_time = (
                                prev_avg + (new_val - prev_avg) / n
                            )
                    else:
                        # If the row doesn't exist (unlikely), insert a minimal record
                        db.add(
                            AIModel(
                                provider=p["provider"],
                                model_id=p["model_id"],
                                category=p.get("category"),
                                rating=p.get("rating"),
                                total_requests=1,
                                totoal_response_time=(
                                    float(p["latency_sec"])
                                    if p["ping_ok"]
                                    and isinstance(p["latency_sec"], (int, float))
                                    else 0.0
                                ),
                                average_response_time=(
                                    float(p["latency_sec"])
                                    if p["ping_ok"]
                                    and isinstance(p["latency_sec"], (int, float))
                                    else 0.0
                                ),
                            )
                        )
                except Exception as e:
                    await db.rollback()
                    print(f"⚠️ Failed to update ping stats for {p['model_id']}: {e}")
            await db.commit()
            wrote = True
    except Exception as e:
        print("⚠️ Could not write ping stats to DB via get_db(). Is FastAPI running?", e)
    return wrote


def persist_to_excel_models(
    categorized: List[Dict[str, Any]], path: str = "models_list.xlsx"
) -> None:
    df = pd.DataFrame(
        categorized, columns=["provider", "model_id", "category", "rating"]
    )
    df.sort_values(by=["provider", "model_id"], inplace=True, ignore_index=True)
    df.to_excel(path, index=False)


def persist_to_excel_pings(
    pings: List[Dict[str, Any]], path: str = "models_ping_results.xlsx"
) -> None:
    cols = [
        "provider",
        "model_id",
        "category",
        "rating",
        "ping_ok",
        "latency_sec",
        "error",
    ]
    df = pd.DataFrame(pings, columns=cols)
    df.sort_values(by=["provider", "model_id"], inplace=True, ignore_index=True)
    df.to_excel(path, index=False)


# =========================
# Orchestrator
# =========================
async def save_models_to_db_and_probe():
    print("📡 Collecting model list from Groq & Mistral")
    raw_models = collect_all_models()

    print("🤖 Categorizing models using Groq REST API")
    categorized = await categorize_models(raw_models)

    # Persist catalog
    wrote_models = await persist_models_to_db(categorized)
    persist_to_excel_models(categorized)
    if wrote_models:
        print("✅ Saved models to DB and Excel")
    else:
        print("✅ Saved models to Excel only (DB for models skipped)")

    print("🛰️ Probing eligible models (text, coding, multimodal) with a 'hi' chat")
    pings = await ping_models(categorized)

    wrote_pings = await persist_pings_to_db(pings)
    persist_to_excel_pings(pings)

    ok_count = sum(1 for p in pings if p["ping_ok"])
    total = len(pings)
    print(f"📊 Ping summary: {ok_count}/{total} succeeded")

    if wrote_pings:
        print("✅ Persisted ping stats to DB and Excel")
    else:
        print("✅ Persisted ping stats to Excel (DB for pings skipped)")


# =========================
# Main execution
# =========================
if __name__ == "__main__":
    asyncio.run(save_models_to_db_and_probe())
