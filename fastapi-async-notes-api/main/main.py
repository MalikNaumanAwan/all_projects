# main/main.py
from fastapi import FastAPI
from core.logging_middleware import LoggingMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.routes.notes import router as notes_router
from main.lifespan import lifespan  # <-- Updated import path
from app.routes import router as api_router  # ← importing the aggregated router)

app = FastAPI(lifespan=lifespan)

# Allow all origins for dev; restrict in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS","DELETE","PUT"],  # ["GET", "POST", "OPTIONS"]
    allow_headers=["*"],  # ["Content-Type", "Authorization"]
)

app.include_router(api_router)  # ← mounts /notes and others
app.add_middleware(LoggingMiddleware)
app.include_router(notes_router, prefix="/api/notes", tags=["Notes"])
