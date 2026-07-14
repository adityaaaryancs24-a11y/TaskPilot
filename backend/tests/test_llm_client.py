from __future__ import annotations

import pytest

from core.llm_client import (
    HeuristicBackend,
    RulesEngineBackend,
    _extract_json,
)


class TestJsonExtraction:
    def test_extract_json_from_plain(self):
        text = '{"key": "value"}'
        parsed, err = _extract_json(text)
        assert parsed == {"key": "value"}
        assert err is None

    def test_extract_json_from_fence(self):
        text = '```json\n{"key": "value"}\n```'
        parsed, err = _extract_json(text)
        assert parsed == {"key": "value"}
        assert err is None

    def test_extract_json_from_markdown(self):
        text = 'Here is the result: ```\n{"key": "value"}\n```'
        parsed, err = _extract_json(text)
        assert parsed == {"key": "value"}
        assert err is None

    def test_extract_json_array(self):
        text = '[{"id": 1}, {"id": 2}]'
        parsed, err = _extract_json(text)
        assert len(parsed) == 2
        assert err is None

    def test_invalid_json(self):
        text = "This is not JSON"
        parsed, err = _extract_json(text)
        assert parsed is None
        assert err is not None


class TestHeuristicBackend:
    @pytest.mark.asyncio
    async def test_generate_json_mode(self):
        backend = HeuristicBackend()
        response = await backend.generate(
            prompt="Test prompt",
            system="prioritization system",
            json_mode=True,
        )
        assert response.parsed_json is not None
        assert isinstance(response.parsed_json, list)

    @pytest.mark.asyncio
    async def test_generate_text_mode(self):
        backend = HeuristicBackend()
        response = await backend.generate(
            prompt="Test prompt",
            system="planning system",
            json_mode=False,
        )
        assert isinstance(response.text, str)
        assert len(response.text) > 0


class TestRulesEngineBackend:
    @pytest.mark.asyncio
    async def test_high_keyword_detection(self):
        backend = RulesEngineBackend()
        response = await backend.generate(
            prompt='[{"title": "Critical production outage"}]',
            system="prioritization system",
            json_mode=True,
        )
        tasks = response.parsed_json
        assert tasks[0]["score"] >= 80

    @pytest.mark.asyncio
    async def test_medium_keyword(self):
        backend = RulesEngineBackend()
        response = await backend.generate(
            prompt='[{"title": "Review PR documentation"}]',
            system="prioritization system",
            json_mode=True,
        )
        tasks = response.parsed_json
        assert 50 <= tasks[0]["score"] <= 70
