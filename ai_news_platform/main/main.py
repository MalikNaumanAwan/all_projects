"""main"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from main.lifespan import lifespan
from routers import admin_router, articles_router
from utils.exceptions import (
    article_processing_exception_handler,
    ArticleProcessingError,
)

app = FastAPI(lifespan=lifespan)
app.add_exception_handler(ArticleProcessingError, article_processing_exception_handler)  # type: ignore
# Mount routes
app.include_router(admin_router.router, prefix="/admin", tags=["Admin"])
app.include_router(articles_router.router, prefix="/articles", tags=["Articles"])

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
