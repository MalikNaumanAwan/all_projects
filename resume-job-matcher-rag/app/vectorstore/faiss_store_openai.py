#faiss_store.py
import faiss
import numpy as np

index_store = {}

def store_vectors(vectors, doc_type: str):
    vectors_np = np.array(vectors).astype("float32")
    index = faiss.IndexFlatL2(vectors_np.shape[1])
    index.add(vectors_np)
    index_store[doc_type] = index

def search_similar_chunks(doc_a: str, doc_b: str):
    index = index_store.get(doc_a)
    query_index = index_store.get(doc_b)
    if not index or not query_index:
        return []

    D, I = index.search(query_index.reconstruct_n(0, query_index.ntotal), 5)
    return I.tolist()
