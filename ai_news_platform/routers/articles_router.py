"""Articles Router"""

from fastapi import APIRouter, HTTPException
import markdown2
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.sessions import get_db_session
from db.models import Article
from schemas.article import IndexArticleOut
from typing import List

from sqlalchemy import select

router = APIRouter()


@router.get("/", response_model=List[IndexArticleOut])
async def get_articles(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Article).order_by(Article.created_at.desc()))
    articles = result.scalars().all()
    return articles


@router.get("/{article_id}")  # ✅ fixed
async def get_article(article_id: str, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return {
        "id": article.id,
        "title": article.title,
        "image_url": article.image_url,
        "source_url": article.source_url,
        "created_at": article.created_at,
        "created_at_formatted": article.created_at.strftime("%B %d, %Y"),
        "content_html": markdown2.markdown(article.content),  # type: ignore
    }
