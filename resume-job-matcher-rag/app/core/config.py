import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # OpenAI & Embeddings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL = os.getenv("MODEL", "gpt-4")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # Uploads
    UPLOAD_FOLDER = "uploads"
    RESUME_DIR = os.path.join(UPLOAD_FOLDER, "resumes")
    JD_DIR = os.path.join(UPLOAD_FOLDER, "jobs")

    # PostgreSQL
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

    DATABASE_URL = os.getenv("DATABASE_URL") or (
        f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

settings = Settings()
