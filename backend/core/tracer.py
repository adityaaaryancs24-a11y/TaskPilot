from __future__ import annotations

import asyncio
import functools
import logging
import time

from core.state import save_trace as _persist_trace

logger = logging.getLogger(__name__)


def trace(step_name: str):
    def decorator(func):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                elapsed = (time.monotonic() - start) * 1000
                logger.info("[TRACE] %s completed in %.1f ms", step_name, elapsed)
                _safe_persist(step_name, elapsed)
                return result
            except Exception as e:
                elapsed = (time.monotonic() - start) * 1000
                logger.error("[TRACE] %s failed at %.1f ms: %s", step_name, elapsed, e)
                _safe_persist(step_name, elapsed, status="error")
                raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                elapsed = (time.monotonic() - start) * 1000
                logger.info("[TRACE] %s completed in %.1f ms", step_name, elapsed)
                await _safe_persist_async(step_name, elapsed)
                return result
            except Exception as e:
                elapsed = (time.monotonic() - start) * 1000
                logger.error("[TRACE] %s failed at %.1f ms: %s", step_name, elapsed, e)
                await _safe_persist_async(step_name, elapsed, status="error")
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _safe_persist(step_name: str, elapsed: float, status: str = "ok"):
    try:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            asyncio.ensure_future(_persist_trace(step_name, elapsed, status=status))
        else:
            logger.debug(
                "[TRACE] %s = %.1fms (not persisted, no event loop)", step_name, elapsed
            )
    except Exception as e:
        logger.debug("Failed to persist trace: %s", e)


async def _safe_persist_async(step_name: str, elapsed: float, status: str = "ok"):
    try:
        await _persist_trace(step_name, elapsed, status=status)
    except Exception as e:
        logger.debug("Failed to persist trace: %s", e)
