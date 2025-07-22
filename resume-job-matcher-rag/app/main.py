# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.routes import match
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 Starting Resume Matcher API...")
    yield
    print("🔻 Shutting down...")

app = FastAPI(title="Resume Job Matcher RAG", lifespan=lifespan)

# ✅ Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Serve /frontend as static files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # root dir
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# ✅ Serve HTML from FastAPI
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    with open(index_file, "r", encoding="utf-8") as f:
        return f.read()

# ✅ Your API
app.include_router(match.router, prefix="/match", tags=["Match"])
