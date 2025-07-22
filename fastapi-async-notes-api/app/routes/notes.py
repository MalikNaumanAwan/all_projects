# app/api/routes/notes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import get_session
from schemas.notes import NoteCreate, NoteOut
from db import crud

router = APIRouter(prefix="/notes", tags=["notes"])
@router.post("/", response_model=NoteOut)
async def create_note(note: NoteCreate, db: AsyncSession = Depends(get_session)):
    return await crud.create_note(note, db)

@router.get("/", response_model=list[NoteOut])
async def read_notes(db: AsyncSession = Depends(get_session)):
    return await crud.get_notes(db)

@router.delete("/{note_id}", status_code=204)
async def delete_note(note_id: int, db: AsyncSession = Depends(get_session)):
    deleted = await crud.delete_note(note_id, db)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    
@router.put("/{note_id}", response_model=NoteOut)
async def update_note(note_id: int, note: NoteCreate, db: AsyncSession = Depends(get_session)):
    return await crud.update_note(note_id, note, db)
