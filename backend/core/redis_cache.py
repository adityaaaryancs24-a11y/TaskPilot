from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._client: Any = None
        self.default_ttl = 3600

    async def initialize(self):
        try:
            import redis.asyncio as aioredis

            self._client = await aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=20,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            await self._client.ping()
            logger.info("Redis cache initialized: %s", self.redis_url)
        except Exception as e:
            logger.warning("Redis not available, falling back to no-op: %s", e)
            self._client = None

    def _key(self, prefix: str, *parts: str) -> str:
        raw = ":".join(parts)
        h = hashlib.md5(raw.encode()).hexdigest()[:16]
        return f"taskpilot:{prefix}:{h}"

    async def get(self, key: str) -> Optional[Any]:
        if not self._client:
            return None
        try:
            val = await self._client.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.debug("Cache get failed: %s", e)
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        if not self._client:
            return
        try:
            await self._client.setex(
                key, ttl or self.default_ttl, json.dumps(value, default=str)
            )
        except Exception as e:
            logger.debug("Cache set failed: %s", e)

    async def delete(self, key: str):
        if not self._client:
            return
        try:
            await self._client.delete(key)
        except Exception as e:
            logger.debug("Cache delete failed: %s", e)

    async def clear_pattern(self, pattern: str):
        if not self._client:
            return
        try:
            keys = await self._client.keys(f"taskpilot:{pattern}:*")
            if keys:
                await self._client.delete(*keys)
        except Exception as e:
            logger.debug("Cache clear failed: %s", e)

    async def cache_embedding(
        self, text: str, embedding: list[float], ttl: int = 86400
    ):
        key = self._key("embedding", text)
        await self.set(key, embedding, ttl=ttl)

    async def get_embedding(self, text: str) -> Optional[list[float]]:
        key = self._key("embedding", text)
        return await self.get(key)

    async def cache_llm_response(
        self, prompt: str, response: Any, model: str = "default", ttl: int = 7200
    ):
        key = self._key("llm", model, prompt)
        await self.set(key, response, ttl=ttl)

    async def get_llm_response(
        self, prompt: str, model: str = "default"
    ) -> Optional[Any]:
        key = self._key("llm", model, prompt)
        return await self.get(key)

    async def invalidate_for_source(self, source: str):
        await self.clear_pattern(f"*{source}*")

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis connection closed")


cache_manager = CacheManager()
