# app/db/models.py
# pylint: disable=not-callable
import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from db.sessions import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    title = Column(String(256), nullable=False)
    source_url = Column(String(512), unique=True, nullable=False)
    image_url = Column(String(512), unique=True, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
