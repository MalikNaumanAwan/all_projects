import asyncio
import requests
from dotenv import load_dotenv
import os
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.dependencies import get_db
from app.auth.models import AIModel

# Load API keys from .env
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


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


async def save_models_to_db():
    print("📡 Collecting model list from Groq & Mistral")
    models = collect_all_models()

    # get AsyncSession from get_db() generator
    async for db in get_db():
        assert isinstance(db, AsyncSession)

        for m in models:
            # Check if model already exists
            result = await db.execute(
                select(AIModel).where(AIModel.model_id == m["model_id"])
            )
            if result.scalar_one_or_none() is None:
                db.add(AIModel(provider=m["provider"], model_id=m["model_id"]))

        await db.commit()

    # Save to Excel
    df = pd.DataFrame(models, columns=["provider", "model_id"])
    output_file = "models_list.xlsx"
    df.to_excel(output_file, index=False)
    print(f"✅ Saved models to DB and to {output_file}")


if __name__ == "__main__":
    asyncio.run(save_models_to_db())
