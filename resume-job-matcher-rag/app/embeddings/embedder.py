from sentence_transformers import SentenceTransformer
from typing import List

# Load once at module level
model = SentenceTransformer("all-mpnet-base-v2")

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using a local model.
    """
    if isinstance(texts, str):
        texts = [texts]
    embeddings = model.encode(texts, convert_to_numpy=True).tolist()
    return embeddings
