# main.py
from fastapi import FastAPI
from app.api.routes.query import router as query_router
from main.lifespan import lifespan
from app.config.settings import settings
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)

# CORS config (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(query_router, prefix="/api/query", tags=["Query"])

# Serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
