from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from core.config import settings
from core.cache import get_embedding_cache, set_embedding_cache

logger = logging.getLogger(__name__)

_model = None
_model_name: Optional[str] = None


def load_embedding_model():
    global _model, _model_name
    if _model is not None and _model_name == settings.embedding_model_name:
        return _model

    model_name = settings.embedding_model_name
    try:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model: %s", model_name)
        _model = SentenceTransformer(model_name)
        _model_name = model_name
        logger.info("Embedding model loaded: %s", model_name)
    except Exception as e:
        logger.warning("Failed to load embedding model '%s': %s", model_name, e)
        logger.warning("Falling back to no-op embeddings")
        _model = None
        _model_name = None
    return _model


def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    model = load_embedding_model()
    if model is None:
        return [[0.0]] * len(texts)
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings.tolist()


def get_embedding(text: str) -> list[float]:
    return get_embeddings_batch([text])[0]


async def get_embedding_cached(text: str) -> list[float]:
    if settings.embedding_cache_enabled:
        cached = await get_embedding_cache(text, settings.embedding_model_name)
        if cached is not None:
            return cached
    emb = get_embedding(text)
    if settings.embedding_cache_enabled:
        await set_embedding_cache(text, settings.embedding_model_name, emb)
    return emb


def cosine_similarity(a: list[float], b: list[float]) -> float:
    arr_a = np.array(a, dtype=np.float32)
    arr_b = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(arr_a)
    norm_b = np.linalg.norm(arr_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(arr_a, arr_b) / (norm_a * norm_b))
