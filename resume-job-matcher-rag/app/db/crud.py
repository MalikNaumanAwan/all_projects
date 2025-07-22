from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import Upload, Match

async def create_upload(db: AsyncSession, resume_filename: str, jd_filename: str):
    upload = Upload(resume_filename=resume_filename, jd_filename=jd_filename)
    db.add(upload)
    await db.commit()
    await db.refresh(upload)
    return upload

async def create_match(db: AsyncSession, upload_id: int, score: float, reasoning: str):
    match = Match(upload_id=upload_id, match_score=score, reasoning=reasoning)
    db.add(match)
    await db.commit()
    await db.refresh(match)
    return match
