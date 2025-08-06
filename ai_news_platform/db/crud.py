from typing import List

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.models import Article
from db.sessions import engine
from schemas.article import FinalArticle

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def save_articles(articles: List[FinalArticle]) -> None:
    """
    Bulk insert list of articles into the database. Skips existing URLs via ON CONFLICT DO NOTHING.
    """
    # Convert HttpUrl fields to str for SQLAlchemy compatibility
    values = []
    for article in articles:
        data = article.model_dump()
        data["source_url"] = str(data["source_url"])
        values.append(data)

    stmt = insert(Article).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=["source_url"])

    async with async_session_maker() as session:
        async with session.begin():
            await session.execute(stmt)
