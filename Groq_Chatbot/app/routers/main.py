# main.py
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.routers.auth_routes import router as auth_router
from app.routers.chat_router import router as chat_router

app = FastAPI()

# CORS & static files
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # one level up
STATIC_DIR = os.path.join(BASE_DIR, "frontend", "static")

if not os.path.exists(STATIC_DIR):
    raise RuntimeError(f"Static directory does not exist: {STATIC_DIR}")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Register routes
app.include_router(auth_router)
app.include_router(chat_router)
