from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.models import Base
from app.db.session import engine
from app.utils.catalog_cache import get_catalog, get_vector_store
from app.core.embeddings import get_embedding_model
import logging
import time
import psutil
import os
import asyncio

logger = logging.getLogger("lifespan")
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🔧 Starting up application...")
    print("⏳ Pre-warming embedding model...")
    start = time.perf_counter()
    await asyncio.get_running_loop().run_in_executor(None, get_embedding_model)
    duration = time.perf_counter() - start
    mem_mb = psutil.Process(os.getpid()).memory_info().rss / 1024**2
    print(
        f"📦 ✅ Embedding model pre-loadedin {duration:.2f}s | Memory: {mem_mb:.1f}MB"
    )

    # Step 1: Init DB
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database schema initialized")
    except Exception as db_err:
        logger.exception(f"❌ DB Init Failed: {db_err}")

    # Step 2: Preload Catalog + FAISS
    try:
        start = time.perf_counter()

        catalog = await get_catalog()  # ✅ AWAIT here
        duration = time.perf_counter() - start
        mem_mb = psutil.Process(os.getpid()).memory_info().rss / 1024**2
        logger.info(f"📦 Catalog loaded in {duration:.2f}s | Memory: {mem_mb:.1f}MB")
        print(f"📦 Loaded {len(catalog)} products from catalog")

        vector_store = await get_vector_store()  # ✅ AWAIT here too
        duration = time.perf_counter() - start
        mem_mb = psutil.Process(os.getpid()).memory_info().rss / 1024**2
        logger.info(f"📈 Vector store ready: {vector_store.__class__.__name__}")
        print(f"📈 Vector store ready: {vector_store.__class__.__name__}")

    except Exception as preload_err:
        logger.exception(f"❌ Asset preload failed: {preload_err}")
        print("CATALOG NOT LOADING")

    yield

    logger.info("📴 Shutting down application...")
