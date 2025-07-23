from langchain_groq import ChatGroq

from app.config.settings import settings


def get_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.OPENAI_API_KEY,
        model_name=settings.MODEL,
        temperature=0.2,
        max_tokens=1024,
    )
 
