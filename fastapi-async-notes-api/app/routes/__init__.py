from fastapi import APIRouter
from app.routes import notes

router = APIRouter()
router.include_router(notes.router)
