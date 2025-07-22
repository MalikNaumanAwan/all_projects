# app/schemas/notes.py

from pydantic import BaseModel

class NoteCreate(BaseModel):
    title: str
    content: str | None = None

class NoteOut(NoteCreate):
    id: int
