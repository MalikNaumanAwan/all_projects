from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import time

EMBED_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
VECTOR_STORE_PATH = Path("vector_store")

# Singleton-style persistent embedding model
_embedding_model = None


def get_embedding_model() -> HuggingFaceEmbeddings:
    global _embedding_model
    if _embedding_model is None:
        print("⏳ Loading HuggingFace embedding model...")
        _embedding_model = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME)
        print("✅ Embedding model loaded.")
    return _embedding_model


def load_or_create_vector_store(texts: list[str]) -> FAISS:
    start = time.perf_counter()
    VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
    index_path = VECTOR_STORE_PATH / "index.faiss"

    embedding_model = get_embedding_model()

    if index_path.exists():
        print("📦 Vector store exists. Loading from disk...")
        vs = FAISS.load_local(
            str(VECTOR_STORE_PATH),
            embeddings=embedding_model,
            allow_dangerous_deserialization=True,
        )
    else:
        print("⚙️ Creating new FAISS vector store from texts...")
        vs = FAISS.from_texts(texts, embedding_model)
        vs.save_local(str(VECTOR_STORE_PATH))
        print("📁 Vector store saved.")

    print(f"✅ FAISS ready in {time.perf_counter() - start:.2f}s")
    return vs
