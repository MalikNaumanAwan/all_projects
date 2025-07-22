from app.embeddings.embedder import get_embeddings
from app.vectorstore.faiss_store import (
    build_store, load_store, save_store,
    store_exists, get_top_k_chunks, chunk_text
)
from app.utils.pdf_loader import parse_pdf
from app.utils.hashing import hash_file
from app.llm.reasoner import generate_match_response
from sqlalchemy.ext.asyncio import AsyncSession

import logging

logger = logging.getLogger(__name__)

async def process_resume_and_jd(resume_path: str, jd_path: str, db: AsyncSession) -> dict:
    try:
        resume_hash = hash_file(resume_path)
        print("processing Resume")
        if store_exists(resume_hash):
            logger.info(f"🔁 Loading FAISS store for {resume_hash}")
            load_store(resume_hash)
            resume_text = parse_pdf(resume_path)  # Needed for full reasoning
        else:
            logger.info(f"📥 Building FAISS store for {resume_hash}")
            resume_text = parse_pdf(resume_path)
            resume_chunks = chunk_text(resume_text)
            resume_vectors = get_embeddings(resume_chunks)
            build_store(resume_chunks, resume_vectors)
            save_store(resume_hash)

        jd_text = parse_pdf(jd_path)
        jd_embedding = get_embeddings(jd_text)[0]
        match_chunks = get_top_k_chunks(jd_embedding, k=5)

        match_result = generate_match_response(
            jd_text=jd_text,
            resume_text=resume_text,
            match_chunks="\n".join(match_chunks),
        )
        print("returned Response from process resume")
        return match_result

    except Exception as e:
        raise RuntimeError(f"Matching failed: {e}")
