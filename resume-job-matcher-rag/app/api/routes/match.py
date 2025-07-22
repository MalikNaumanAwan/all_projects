#match.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.services.rag_service import process_resume_and_jd
from app.db.db_session import get_db
from app.utils.file_handler import save_file  # ✅ Import the save utility

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/")
async def match_files(
    resume: UploadFile = File(...),
    jd: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Resume content type: {resume.content_type}")
    logger.info(f"JD content type: {jd.content_type}")

    if resume.content_type != "application/pdf" or jd.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        # ✅ Save files to disk before passing to RAG
        resume_path = await save_file(resume, "resumes")
        jd_path = await save_file(jd, "jobs")

        response = await process_resume_and_jd(resume_path, jd_path, db)
        logger.info(f"Match response: {response}")
        print(response)
        return JSONResponse(content=response, media_type="application/json")
    except Exception as e:
        logger.exception("Matching failed:")
        raise HTTPException(status_code=500, detail=f"Matching failed: {e}")
