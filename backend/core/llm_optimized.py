from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from core.redis_cache import cache_manager


logger = logging.getLogger(__name__)


@dataclass
class LLMRequest:
    prompt: str
    model: str = "default"
    max_tokens: int = 500
    temperature: float = 0.3


@dataclass
class LLMResponse:
    content: str
    tokens_used: int = 0
    model: str = ""
    latency_ms: float = 0.0
    cached: bool = False
    parsed_json: Optional[Any] = field(default=None)


class OptimizedLLMClient:
    def __init__(self):
        self.batch_size = 10
        self.max_retries = 3
        self._tokenizers: dict[str, Any] = {}

    def _get_tokenizer(self, model_name: str):
        if model_name not in self._tokenizers:
            try:
                from transformers import AutoTokenizer

                self._tokenizers[model_name] = AutoTokenizer.from_pretrained(model_name)
            except Exception:
                try:
                    import tiktoken

                    self._tokenizers[model_name] = tiktoken.encoding_for_model(
                        "gpt-3.5-turbo"
                    )
                except Exception:
                    self._tokenizers[model_name] = None
        return self._tokenizers.get(model_name)

    def count_tokens(self, text: str, model: str = "default") -> int:
        tokenizer = self._get_tokenizer(model)
        if tokenizer is not None:
            try:
                return len(tokenizer.encode(text))
            except Exception:
                pass
        return int(len(text.split()) * 1.3)

    def truncate_to_limit(
        self, text: str, max_tokens: int, model: str = "default"
    ) -> str:
        tokenizer = self._get_tokenizer(model)
        if tokenizer is not None:
            try:
                tokens = tokenizer.encode(text)
                if len(tokens) > max_tokens:
                    return tokenizer.decode(tokens[:max_tokens])
            except Exception:
                pass
        words = text.split()
        if len(words) > max_tokens:
            return " ".join(words[:max_tokens])
        return text

    async def batch_process(
        self, prompts: list[str], model: str = "default"
    ) -> list[str]:
        if not prompts:
            return []

        cached_responses: list[tuple[int, str]] = []
        uncached_indices: list[int] = []
        uncached_prompts: list[str] = []

        for idx, prompt in enumerate(prompts):
            cached = await cache_manager.get_llm_response(prompt, model)
            if cached is not None:
                cached_responses.append((idx, cached))
            else:
                uncached_indices.append(idx)
                uncached_prompts.append(prompt)

        batch_results: list[str] = []
        if uncached_prompts:
            for i in range(0, len(uncached_prompts), self.batch_size):
                batch = uncached_prompts[i : i + self.batch_size]
                combined = "\n\n---\n\n".join(
                    f"Request {j + 1}: {p}" for j, p in enumerate(batch)
                )
                response = await self._make_llm_call(combined, model)
                parsed = self._parse_batch_response(response, len(batch))
                batch_results.extend(parsed)
                for prompt, resp in zip(batch, parsed):
                    await cache_manager.cache_llm_response(prompt, resp, model)

        final: list[Optional[str]] = [None] * len(prompts)
        for idx, resp in cached_responses:
            final[idx] = resp
        for i, resp in enumerate(batch_results):
            final[uncached_indices[i]] = resp

        return [r for r in final if r is not None]

    async def _make_llm_call(self, prompt: str, model: str) -> str:
        from core.llm_client import call_llm

        start = time.monotonic()
        response = await call_llm(prompt=prompt, temperature=0.2)
        latency = (time.monotonic() - start) * 1000
        logger.debug("LLM call completed in %.0fms for model=%s", latency, model)
        return response.text

    def _parse_batch_response(self, combined: str, num_responses: int) -> list[str]:
        sections = combined.split("\n\n---\n\n")
        return sections[:num_responses]


optimized_llm = OptimizedLLMClient()
