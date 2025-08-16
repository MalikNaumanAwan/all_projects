import os
import requests
import asyncio
import pandas as pd
from time import sleep
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.dependencies import get_db
from app.auth.models import AIModel
import httpx

# =========================
# Load environment variables
# =========================
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


# =========================
# Fetch models from providers
# =========================
def get_models_from_groq():
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])


def get_models_from_mistral():
    url = "https://api.mistral.ai/v1/models"
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])


def collect_all_models():
    all_models = []

    for model in get_models_from_groq():
        all_models.append({"provider": "Groq", "model_id": model["id"]})

    for model in get_models_from_mistral():
        all_models.append({"provider": "Mistral", "model_id": model["id"]})

    return all_models


# =========================
# Fetch real-time info from Serper
# =========================
def search_model_info(model_id):
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": model_id}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        snippet = data.get("answer_box", {}).get("snippet")
        if snippet:
            return snippet
        elif "organic" in data and len(data["organic"]) > 0:
            return data["organic"][0].get("snippet", "No description available.")
        else:
            return "No description available."
    except Exception as e:
        print(f"Error fetching info for {model_id}: {e}")
        return "No description available."


# =========================
# Categorize models using Groq REST API (async)
# =========================
# =========================
# Categorize & Rate models using Groq REST API (async)
# =========================
async def categorize_models(models):
    categorized_models = []

    async with httpx.AsyncClient(timeout=30) as client:
        for model in models:
            model_id = model.get("model_id", "unknown")
            try:
                print("Model: ", model_id)
                description = search_model_info(model_id)

                messages = [
                    {
                        "role": "user",
                        "content": f"""
                        You are an AI model evaluator.
                        Based on this description, classify the model into a SINGLE-WORD category
                        (coding, text, vision, audio, multimodal).
                        Also, rate the model performance considering its category on a scale of 1–10, where:
                        10 = state-of-the-art,
                        7–9 = strong performer,
                        4–6 = average,
                        1–3 = weak/obsolete.

                        Respond in strict JSON with keys: category, rating.

                        Model ID: {model_id}
                        Description: {description}
                        """,
                    }
                ]

                payload = {
                    "model": "openai/gpt-oss-120b",
                    "messages": messages,
                    "temperature": 0,
                    "stream": False,
                }
                url = "https://api.groq.com/openai/v1/chat/completions"
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()

                # Try parsing JSON
                import json

                try:
                    parsed = json.loads(content)
                    category = parsed.get("category", "unknown")
                    rating = parsed.get("rating", "unknown")
                    print("category: ", category)
                    print("Rating: ", rating)
                except Exception:
                    category, rating = "unknown", "unknown"

                categorized_models.append(
                    {
                        "provider": model["provider"],
                        "model_id": model_id,
                        "category": category,
                        "rating": rating,
                    }
                )

                sleep(0.9)  # avoid hitting limits
            except Exception as e:
                print(f"Error categorizing model {model_id}: {e}")
                categorized_models.append(
                    {
                        "provider": model.get("provider", "unknown"),
                        "model_id": model_id,
                        "category": "unknown",
                        "rating": "unknown",
                    }
                )

    return categorized_models


# =========================
# Save to DB & Excel
# =========================
async def save_models_to_db():
    print("📡 Collecting model list from Groq & Mistral")
    models = collect_all_models()

    print("🤖 Categorizing models using Groq REST API")
    models = await categorize_models(models)

    wrote_to_db = False
    try:
        async for db in get_db():  # works when app is running
            assert isinstance(db, AsyncSession)
            for m in models:
                try:
                    result = await db.execute(
                        select(AIModel).where(AIModel.model_id == m["model_id"])
                    )
                    if result.scalar_one_or_none() is None:
                        db.add(
                            AIModel(
                                provider=m["provider"],
                                model_id=m["model_id"],
                                category=m.get("category"),
                                rating=m.get("rating"),
                            )
                        )
                except Exception as e:
                    await db.rollback()
                    print(f"⚠️ Failed to insert {m['model_id']}: {e}")
            await db.commit()
            wrote_to_db = True
    except Exception as e:
        print(
            "⚠️ Could not write to DB via get_db(). Did you forget to start FastAPI?", e
        )

    # Excel output always works
    df = pd.DataFrame(models, columns=["provider", "model_id", "category", "rating"])
    df.to_excel("models_list.xlsx", index=False)

    if wrote_to_db:
        print("✅ Saved models to DB and Excel")
    else:
        print("✅ Saved models to Excel only (DB skipped)")


# =========================
# Main execution
# =========================
if __name__ == "__main__":
    asyncio.run(save_models_to_db())
