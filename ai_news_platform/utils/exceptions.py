# app/core/exception.py

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


class ArticleProcessingError(Exception):
    """ArticleProcessingError"""

    def __init__(self, detail: str = "Failed to process article chunk."):
        self.detail = detail


async def article_processing_exception_handler(
    request: Request, exc: ArticleProcessingError
):
    """article_processing_exception_handler"""
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "ArticleProcessingError", "detail": exc.detail},
    )
