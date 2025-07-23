from contextlib import asynccontextmanager
from app.db.models import Base
from app.db.session import engine
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app):
    logger.info("🔧 Starting up application...")
    
    # Optional: Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database schema initialized")

    # Optional: preload FAISS or other data into memory

    yield

    logger.info("📴 Shutting down application...")
    # Cleanups go here (e.g., cache, file handles, etc.)
