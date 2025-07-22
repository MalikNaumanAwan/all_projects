#faiss_store.py
import faiss
import numpy as np

# FAISS index setup
dimension = 768  # for all-mpnet-base-v2
index = faiss.IndexFlatL2(dimension)
stored_chunks = []  # List[str]

def reset_store():
    global index, stored_chunks
    index.reset()
    stored_chunks = []

def store_vectors(chunks: list[str], embeddings: list[list[float]]):
    global stored_chunks

    vectors_np = np.array(embeddings).astype("float32")
    index.add(vectors_np)
    stored_chunks.extend(chunks)

def get_top_k_chunks(query_embedding: list[float], k=5) -> list[str]:
    if index.ntotal == 0:
        return []

    query_np = np.array([query_embedding]).astype("float32")
    _, indices = index.search(query_np, k)

    return [stored_chunks[i] for i in indices[0] if i < len(stored_chunks)]

def chunk_text(text: str, max_tokens: int = 100) -> list[str]:
    """
    Naive chunking: split by sentences or token limits.
    Replace with tiktoken/regex-based chunking later.
    """
    import textwrap
    return textwrap.wrap(text, width=max_tokens)
