"""
app/ai/embedding_model.py

Reusable embedding functions using Hugging Face's sentence-transformers,
specifically sentence-transformers/all-MiniLM-L6-v2 (configured in
app/core/config.py, not hardcoded here, so the model can be swapped via
the EMBEDDING_MODEL_NAME env var without a code change).

Model loading:
The model is loaded once per process via a cached singleton
(get_embedding_model), since downloading/loading weights from disk is
expensive and the model itself is stateless and safe to reuse across
requests. In production, the first call after a cold start will be slow
(model download + load); subsequent calls reuse the cached instance.
"""

import logging
from functools import lru_cache
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    """
    Loads and caches the sentence-transformers model named in
    settings.EMBEDDING_MODEL_NAME. @lru_cache with no arguments makes this
    a singleton — the model loads on the first call and every subsequent
    call reuses the same in-memory instance.
    """
    logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL_NAME)
    model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    logger.info("Embedding model loaded successfully.")
    return model


def generate_embedding(text: str) -> List[float]:
    """
    Generates a single embedding vector for one piece of text (e.g. a
    resume's raw text or a job description). Returns a plain Python list,
    not a numpy array, so the result can be JSON-serialized for storage in
    the embedding_vector column.

    Raises ValueError for empty/whitespace-only input rather than passing
    it to the model, since an embedding of nothing isn't meaningful and
    would silently produce a low-information vector.
    """
    if not text or not text.strip():
        raise ValueError("Cannot generate an embedding for empty text.")

    model = get_embedding_model()
    vector = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
    return vector.tolist()


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Batch version of generate_embedding — encodes multiple texts in one
    model call, which is significantly faster than looping
    generate_embedding() for bulk operations (e.g. re-embedding every
    resume after a model upgrade).
    """
    if not texts:
        return []

    model = get_embedding_model()
    vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=16)
    return [v.tolist() for v in vectors]


def cosine_similarity(vector_a: List[float], vector_b: List[float]) -> float:
    """
    Computes cosine similarity between two embedding vectors using
    scikit-learn. Returns a float clipped to [0, 1] — normalized
    all-MiniLM-L6-v2 embeddings produce cosine similarities in this range
    in practice, but the clip guards against floating-point edge cases
    (e.g. -0.0000001 from rounding) leaking into a score calculation.
    """
    a = np.array(vector_a, dtype=np.float32).reshape(1, -1)
    b = np.array(vector_b, dtype=np.float32).reshape(1, -1)

    if a.shape[1] != b.shape[1]:
        raise ValueError(f"Embedding dimension mismatch: {a.shape[1]} vs {b.shape[1]}.")

    score = sklearn_cosine_similarity(a, b)[0][0]
    return float(max(0.0, min(1.0, score)))
