from langchain_community.vectorstores import FAISS 
from langchain_huggingface import HuggingFaceEmbeddings 
from app.config.settings import settings
import os
from functools import lru_cache
@lru_cache(maxsize=1)
def is_faiss_index_available(index_path: str) -> bool:
    return (
        os.path.exists(index_path)
        and os.path.isfile(os.path.join(index_path, "index.faiss"))
        and os.path.isfile(os.path.join(index_path, "index.pkl"))
    )

@lru_cache(maxsize=1)
def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"}  # change to "cuda" if available
    )

@lru_cache(maxsize=1)
def load_or_create_vector_store(text_chunks: list[str]) -> FAISS:
    embedding_model = get_embedding_model()
    index_path = settings.FAISS_INDEX_PATH

    if is_faiss_index_available(index_path):
        return FAISS.load_local(index_path, embeddings=embedding_model, allow_dangerous_deserialization=True) 
        #Do NOT Do This If: You're loading files uploaded by users, You're downloading files from a remote source (like S3, web, etc.),  You aren't sure who created the file
    else:
        vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embedding_model)
        vectorstore.save_local(index_path) #, safe=True for safety
        return vectorstore
 
