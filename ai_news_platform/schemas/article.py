# app/schemas/article.py

from typing import List
from pydantic import BaseModel, Field, HttpUrl, computed_field
from uuid import UUID
from datetime import datetime


class ArticleBase(BaseModel):
    title: str = Field(..., max_length=256)
    source_url: str = Field(..., max_length=512)
    image_url: str = Field(..., max_length=512)


class ArticleCreate(BaseModel):
    title: str = Field(..., max_length=256)
    source_url: str = Field(..., max_length=512)
    image_url: str = Field(..., max_length=512)
    content: str = Field(..., min_length=1)


class FinalArticle(BaseModel):
    title: str = Field(..., max_length=256)
    source_url: str = Field(..., max_length=512)
    image_url: str = Field(..., max_length=512)
    content: str = Field(..., min_length=1)


class ArticleChunkBase(BaseModel):
    title: str = Field(..., max_length=256)
    source_url: str = Field(..., max_length=512)
    image_url: str = Field(..., max_length=512)
    chunk_index: str = Field(..., max_length=32)
    content: List[str]


class IndexArticleOut(BaseModel):
    id: UUID
    title: str
    image_url: HttpUrl | str  # Accepts relative URLs
    source_url: str
    created_at: datetime  # ✅ Fix: allow datetime object

    @computed_field
    @property
    def created_at_formatted(self) -> str:
        return self.created_at.strftime("%d %b %Y")

    def __init__(self, **data):
        super().__init__(**data)
        self.created_at = data["created_at"]


class ArticleOut(BaseModel):
    id: UUID
    title: str
    image_url: HttpUrl | str  # Accepts relative URLs
    source_url: HttpUrl | str
    created_at: datetime  # ✅ Fix: allow datetime object
    created_at_formatted: str
    content_html: str


"""  @computed_field
    @property
    def created_at_formatted(self) -> str:
        return self.created_at.strftime("%d %b %Y")

    def __init__(self, **data):
        super().__init__(**data)
        self.created_at = data["created_at"]
 """
