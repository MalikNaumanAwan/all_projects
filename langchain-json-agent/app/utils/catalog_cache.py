import logging
import asyncio
from typing import List, Dict, Optional
from app.core.loader import load_json_data_async
from app.core.embeddings import load_or_create_vector_store

logger = logging.getLogger(__name__)

# Simple async cache store
_catalog_data: Optional[List[Dict]] = None
_vector_store = None
_lock = asyncio.Lock()
_catalog_data_lock = asyncio.Lock()
_vector_store_lock = asyncio.Lock()


async def get_catalog() -> List[Dict]:
    global _catalog_data

    async with _catalog_data_lock:
        if _catalog_data is None:
            try:
                _catalog_data = await load_json_data_async()
            except Exception as e:
                logger.exception("❌ Failed to load catalog data")
                print(f"[get_catalog] ❌ Error: {e}")
                _catalog_data = []

    return _catalog_data


async def get_vector_store():
    global _vector_store

    async with _vector_store_lock:
        if _vector_store is None:
            try:
                data = await get_catalog()
                if not data:
                    raise ValueError("Catalog data is empty or failed to load.")

                product_texts = [
                    f"{item['name']} - {item.get('description', '')}" for item in data
                ]

                # 🔄 FAISS is sync, so call it in thread
                print("....Loading Vectors....")
                loop = asyncio.get_running_loop()
                _vector_store = await loop.run_in_executor(
                    None, load_or_create_vector_store, product_texts
                )

            except Exception as e:
                logger.exception("❌ Failed to create/load FAISS vector store")
                print(f"[get_vector_store] ❌ Error: {e}")
                _vector_store = None

    return _vector_store
