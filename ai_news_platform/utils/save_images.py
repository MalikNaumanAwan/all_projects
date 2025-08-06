import aiohttp
import uuid
from typing import List
from pathlib import Path
from fastapi import HTTPException
from pydantic import HttpUrl

from schemas.article import ArticleCreate  # Update import to your structure

STATIC_IMAGES_DIR = Path(__file__).resolve().parent.parent / "static" / "images"
STATIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


async def download_image(
    session: aiohttp.ClientSession, url: HttpUrl, dest_path: Path
) -> None:
    try:
        async with session.get(str(url)) as response:
            if response.status != 200:
                raise HTTPException(
                    status_code=400, detail=f"Failed to fetch image: {url}"
                )
            with open(dest_path, "wb") as f:
                f.write(await response.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image download error: {e}")


async def process_article_images(articles: List[ArticleCreate]) -> List[ArticleCreate]:
    cleaned_articles: List[ArticleCreate] = []

    async with aiohttp.ClientSession() as session:
        for article in articles:
            if article.image_url:
                image_ext = Path(str(article.image_url)).suffix or ".jpg"
                image_uuid = f"{uuid.uuid4()}{image_ext}"
                image_path = STATIC_IMAGES_DIR / image_uuid

                await download_image(session, article.image_url, image_path)

                updated_article = article.model_copy(
                    update={"image_url": f"/static/images/{image_uuid}"}
                )
                cleaned_articles.append(updated_article)
            else:
                cleaned_articles.append(article)

    return cleaned_articles
