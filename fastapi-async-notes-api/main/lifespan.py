# app/lifespan.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 App is starting up...")
    yield
    print("🛑 App is shutting down...")
