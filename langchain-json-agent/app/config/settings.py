import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    #General
    APP_NAME = os.getenv("APP_NAME", "LangChain JSON Agent")
    FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./faiss_index")
    # OpenAI & Embeddings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL = os.getenv("MODEL", "gpt-4")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    # PostgreSQL
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    json_data_path = os.getenv("JSON_DATA_PATH")
    DATABASE_URL = os.getenv("DATABASE_URL") or (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

settings = Settings()
