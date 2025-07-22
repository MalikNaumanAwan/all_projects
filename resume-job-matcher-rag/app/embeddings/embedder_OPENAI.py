import openai
from app.core.config import settings

def get_embeddings(text: str):
    openai.api_key = settings.OPENAI_API_KEY
    response = openai.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text
    )
    return [record.embedding for record in response.data]
