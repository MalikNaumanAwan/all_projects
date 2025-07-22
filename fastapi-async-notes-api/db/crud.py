# app/db/crud.py

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.models import Note
from schemas.notes import NoteCreate

async def create_note(note_data: NoteCreate, db: AsyncSession) -> Note:
    note = Note(**note_data.model_dump())
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note

async def get_notes(db: AsyncSession):
    result = await db.execute(select(Note))
    return result.scalars().all()

async def delete_note(note_id: int, db: AsyncSession):
    note = await db.get(Note, note_id)
    if note is None:
        return False
    await db.delete(note)
    await db.commit()
    return True

async def update_note(note_id: int, note: NoteCreate, db: AsyncSession):
    result = await db.execute(select(Note).where(Note.id == note_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")
    
    existing.title = note.title
    existing.content = note.content
    await db.commit()
    await db.refresh(existing)
    return existing
