#faiss_store.py
import faiss
import numpy as np
import os
import pickle

dimension = 768
index = None
stored_chunks = []

def get_index_path(resume_hash: str):
    base_dir = os.path.join(os.path.dirname(__file__), 'resumes')
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, f"index_{resume_hash}")


def load_store(resume_hash: str):
    global index, stored_chunks
    path = get_index_path(resume_hash)
    index = faiss.read_index(f"{path}.faiss")
    with open(f"{path}.pkl", "rb") as f:
        stored_chunks = pickle.load(f)

def ensure_directory_exists(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def save_store(resume_hash: str):
    path = get_index_path(resume_hash)
    ensure_directory_exists(path + ".faiss")  # Ensures parent directory exists
    faiss.write_index(index, f"{path}.faiss")
    with open(f"{path}.pkl", "wb") as f:
        pickle.dump(stored_chunks, f)


def build_store(chunks: list[str], embeddings: list[list[float]]):
    global index, stored_chunks
    index = faiss.IndexFlatL2(dimension)
    stored_chunks = chunks
    vectors_np = np.array(embeddings).astype("float32")
    index.add(vectors_np)

def store_exists(resume_hash: str):
    path = get_index_path(resume_hash)
    return os.path.exists(f"{path}.faiss") and os.path.exists(f"{path}.pkl")

def get_top_k_chunks(query_embedding: list[float], k=5) -> list[str]:
    if index is None or index.ntotal == 0:
        return []

    query_np = np.array([query_embedding]).astype("float32")
    _, indices = index.search(query_np, k)
    return [stored_chunks[i] for i in indices[0] if i < len(stored_chunks)]

def chunk_text(text: str, max_tokens: int = 100) -> list[str]:
    import textwrap
    return textwrap.wrap(text, width=max_tokens)
