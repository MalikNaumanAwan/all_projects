"""lifespan.py"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """lifespan"""
    # Startup tasks
    print("[✓] Application startup")
    yield
    # Shutdown tasks
    print("[✓] Application shutdown")
