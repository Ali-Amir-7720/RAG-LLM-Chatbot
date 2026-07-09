import hashlib
import random
from typing import List


def get_embedding(text: str) -> List[float]:
    """
    Generates a deterministic 1536-dimensional normalized vector for a given text.
    This provides a zero-dependency mock embedding model for local development/test compatibility
    with pgvector's strict dimensions, returning consistent embeddings for identical inputs.
    """
    # Deterministic seed from text hash
    hasher = hashlib.sha256(text.encode("utf-8"))
    seed = int(hasher.hexdigest(), 16) % (2**32)
    
    # Initialize deterministic local generator
    rng = random.Random(seed)
    embedding = [rng.uniform(-1.0, 1.0) for _ in range(1536)]
    
    # Normalize the vector to unit length (improves cosine similarity modeling stability)
    norm = sum(x * x for x in embedding) ** 0.5
    if norm > 0:
        embedding = [x / norm for x in embedding]
        
    return embedding
