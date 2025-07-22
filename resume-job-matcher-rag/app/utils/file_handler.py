#file_handler.py
import os
from fastapi import UploadFile
from app.core.config import settings

async def save_file(upload_file: UploadFile, subdir: str) -> str:

    folder = os.path.join(settings.UPLOAD_FOLDER, subdir)
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, upload_file.filename)
    print(f"Saving {upload_file.filename} to {file_path}")
    with open(file_path, "wb") as buffer:
        buffer.write(await upload_file.read())
    return file_path
