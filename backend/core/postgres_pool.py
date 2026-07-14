from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

import asyncpg
from asyncpg.pool import Pool
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class PostgresManager:
    _instance = None
    _pool: Optional[Pool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(
        self,
        dsn: str,
        min_size: int = 10,
        max_size: int = 50,
        command_timeout: int = 30,
    ):
        if self._pool is not None:
            return
        try:
            self._pool = await asyncpg.create_pool(
                dsn,
                min_size=min_size,
                max_size=max_size,
                command_timeout=command_timeout,
                max_inactive_connection_lifetime=300,
                timeout=10,
            )
            logger.info(
                "PostgreSQL pool initialized: %d-%d connections", min_size, max_size
            )
            async with self._pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info("Connected to: %s", version[:80])
        except Exception as e:
            logger.error("Failed to initialize PostgreSQL: %s", e)
            raise

    @asynccontextmanager
    async def get_connection(self):
        if self._pool is None:
            raise RuntimeError("Database not initialized")
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                async with self._pool.acquire() as conn:
                    yield conn
                    return
            except asyncpg.exceptions.InterfaceError as e:
                if "connection already closed" in str(e):
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(
                            "Connection closed, retrying (%d/%d)",
                            retry_count,
                            max_retries,
                        )
                        await asyncio.sleep(0.1 * retry_count)
                        continue
                    raise
                raise
            except Exception as e:
                logger.error("Database error: %s", e)
                raise

    async def execute(self, query: str, *args) -> Any:
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)

    async def fetch_one(self, query: str, *args) -> Any:
        async with self.get_connection() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch_all(self, query: str, *args) -> Any:
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)

    async def fetch_val(self, query: str, *args) -> Any:
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args)

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgreSQL pool closed")

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def health_check(self) -> bool:
        try:
            val = await self.fetch_val("SELECT 1")
            return val == 1
        except Exception as e:
            logger.error("Health check failed: %s", e)
            return False


db_manager = PostgresManager()
