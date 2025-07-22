#rag_service.py
import os
from app.utils.file_handler import save_file
from app.utils.pdf_loader import parse_pdf
from app.embeddings.embedder_OPENAI import get_embeddings
from app.vectorstore.faiss_store import store_vectors, search_similar_chunks
from app.llm.reasoner import generate_match_response
from app.db.crud import create_upload, create_match
from app.db.db_session import get_db

async def process_resume_and_jd(resume_file, jd_file, db):
    # Save uploaded files to disk
    resume_path = await save_file(resume_file, "resumes")
    jd_path = await save_file(jd_file, "jobs")

    # Parse text from PDFs
    resume_text = parse_pdf(resume_path)
    jd_text = parse_pdf(jd_path)

    # Generate embeddings
    resume_embeddings = get_embeddings(resume_text)
    jd_embeddings = get_embeddings(jd_text)

    # Store vectors in in-memory FAISS index
    store_vectors(resume_embeddings, "resume")
    store_vectors(jd_embeddings, "jd")

    # Retrieve similar chunks (this can be improved later with chunking logic)
    similar_chunk_ids = search_similar_chunks("resume", "jd")

    # Generate reasoning/match result using GPT
    result = generate_match_response(
        jd_text=jd_text,
        resume_text=resume_text,
        match_chunks=similar_chunk_ids
    )
    # Save upload record
    upload = await create_upload(db, os.path.basename(resume_path), os.path.basename(jd_path))

    # Save match record
    await create_match(db, upload.id, result["score"], result["reasoning"])

    return {
        "match_result": result
    }
