from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.config.settings import settings
import os


def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"}  # change to "cuda" if available
    )


def load_or_create_vector_store(text_chunks: list[str]) -> FAISS:
    embedding_model = get_embedding_model()
    index_path = settings.faiss_index_path

    if os.path.exists(index_path):
        return FAISS.load_local(index_path, embeddings=embedding_model)
    else:
        vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embedding_model)
        vectorstore.save_local(index_path)
        return vectorstore
 
