from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

from core.config import settings

logger = logging.getLogger(__name__)

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis

            _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
            logger.info("Redis client created: %s", settings.redis_url)
        except Exception as e:
            logger.warning("Redis unavailable, caching disabled: %s", e)
            _redis_client = None
    return _redis_client


def _make_key(prefix: str, *args, **kwargs) -> str:
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    h = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{prefix}:{h}"


async def cache_get(key: str) -> Optional[Any]:
    client = _get_redis()
    if client is None:
        return None
    try:
        val = await client.get(key)
        return json.loads(val) if val else None
    except Exception as e:
        logger.debug("Cache get failed: %s", e)
        return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    client = _get_redis()
    if client is None:
        return False
    try:
        await client.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.debug("Cache set failed: %s", e)
        return False


async def cache_delete(key: str) -> bool:
    client = _get_redis()
    if client is None:
        return False
    try:
        await client.delete(key)
        return True
    except Exception as e:
        logger.debug("Cache delete failed: %s", e)
        return False


async def cache_delete_pattern(pattern: str) -> int:
    client = _get_redis()
    if client is None:
        return 0
    try:
        keys = await client.keys(pattern)
        if keys:
            return await client.delete(*keys)
        return 0
    except Exception as e:
        logger.debug("Cache delete pattern failed: %s", e)
        return 0


async def get_llm_cache(prompt: str, system: Optional[str] = None) -> Optional[str]:
    key = _make_key("llm", prompt, system)
    return await cache_get(key)


async def set_llm_cache(
    prompt: str, system: Optional[str], response: str, ttl: int = 7200
):
    key = _make_key("llm", prompt, system)
    await cache_set(key, response, ttl=ttl)


async def get_embedding_cache(text: str, model: str) -> Optional[list[float]]:
    key = _make_key("emb", text, model)
    return await cache_get(key)


async def set_embedding_cache(text: str, model: str, embedding: list[float]):
    key = _make_key("emb", text, model)
    await cache_set(key, embedding, ttl=86400)


async def health_check() -> bool:
    client = _get_redis()
    if client is None:
        return False
    try:
        await client.ping()
        return True
    except Exception:
        return False
