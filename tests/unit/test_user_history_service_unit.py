import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.llm.config import LLMProvider
from app.service.user_history_service import UserHistoryService


@pytest.fixture
def service():
    svc = UserHistoryService(db=Mock())
    svc.primary_provider = LLMProvider.OLLAMA
    svc.fallback_provider = LLMProvider.GROQ
    return svc


def test_get_user_history_aggregates_all_sections(service):
    with patch(
        "app.service.user_history_service.db_repository.get_user_moods",
        return_value=[{"id": 1}],
    ), patch(
        "app.service.user_history_service.db_repository.get_user_feedback",
        return_value=[{"id": 2}, {"id": 3}],
    ), patch(
        "app.service.user_history_service.db_repository.get_user_activities",
        return_value=[],
    ):
        result = service.get_user_history("u1")

    assert result["total_moods"] == 1
    assert result["total_feedback"] == 2
    assert result["total_activities"] == 0


def test_get_user_history_re_raises_repository_exception(service):
    with patch(
        "app.service.user_history_service.db_repository.get_user_moods",
        side_effect=RuntimeError("db unavailable"),
    ):
        with pytest.raises(RuntimeError, match="db unavailable"):
            service.get_user_history("u1")


def test_get_periodic_mood_rejects_invalid_date_range(service):
    with pytest.raises(ValueError, match="from_date must be before or equal to to_date"):
        asyncio.run(
            service.get_periodic_mood(
                user_id="u1",
                from_date=datetime(2024, 2, 1),
                to_date=datetime(2024, 1, 1),
            )
        )


def test_get_periodic_mood_success_flow(service):
    moods = [
        {"mood_analysed": "happy", "confidence_score": 0.9},
        {"mood_analysed": "sad", "confidence_score": 0.6},
    ]
    analysis = {
        "period_analysis": "Mixed emotions over period",
        "recommendation": "Take a short break daily",
        "llm_provider": "ollama",
    }

    with patch(
        "app.service.user_history_service.db_repository.get_user_moods_in_period",
        return_value=moods,
    ):
        service._generate_mood_analysis = AsyncMock(return_value=analysis)
        result = asyncio.run(
            service.get_periodic_mood(
                user_id="u1",
                from_date=datetime(2024, 1, 1),
                to_date=datetime(2024, 1, 31),
            )
        )

    assert result["mood_statistics"]["total_moods"] == 2
    assert result["period_analysis"] == "Mixed emotions over period"
    assert result["llm_provider"] == "ollama"


def test_calculate_mood_statistics_for_empty_data(service):
    result = service._calculate_mood_statistics([])
    assert result["total_moods"] == 0
    assert result["mood_distribution"] == {}


def test_calculate_mood_statistics_with_values(service):
    moods = [
        {"mood_analysed": "happy", "confidence_score": 0.9},
        {"mood_analysed": "happy", "confidence_score": 0.7},
        {"mood_analysed": "calm", "confidence_score": 0.8},
    ]
    result = service._calculate_mood_statistics(moods)
    assert result["most_common_mood"] == "happy"
    assert result["least_common_mood"] == "calm"
    assert result["average_confidence"] == round((0.9 + 0.7 + 0.8) / 3, 3)


def test_generate_mood_analysis_primary_success(service):
    service._call_llm = AsyncMock(return_value='{"period_analysis":"good","recommendation":"keep going"}')

    result = asyncio.run(
        service._generate_mood_analysis(
            user_id="u1",
            mood_data=[],
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 1, 2),
        )
    )

    assert result["period_analysis"] == "good"
    assert result["llm_provider"] == LLMProvider.OLLAMA.value


def test_generate_mood_analysis_uses_fallback(service):
    service._call_llm = AsyncMock(
        side_effect=[
            RuntimeError("primary fail"),
            '{"period_analysis":"fallback","recommendation":"fallback rec"}',
        ]
    )

    result = asyncio.run(
        service._generate_mood_analysis(
            user_id="u1",
            mood_data=[],
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 1, 2),
        )
    )

    assert result["period_analysis"] == "fallback"
    assert result["llm_provider"] == LLMProvider.GROQ.value


def test_generate_mood_analysis_returns_default_when_all_fail(service):
    service._call_llm = AsyncMock(side_effect=RuntimeError("all failed"))

    result = asyncio.run(
        service._generate_mood_analysis(
            user_id="u1",
            mood_data=[],
            from_date=datetime(2024, 1, 1),
            to_date=datetime(2024, 1, 2),
        )
    )

    assert result["llm_provider"] == "default"
    assert "Unable to generate analysis" in result["period_analysis"]


def test_format_mood_data_for_llm_with_and_without_data(service):
    formatted_empty = service._format_mood_data_for_llm([])
    assert "No mood data available" in formatted_empty

    formatted = service._format_mood_data_for_llm(
        [{"created_at": "2024-01-01", "mood_analysed": "happy", "confidence_score": 0.91}]
    )
    assert "2024-01-01" in formatted
    assert "happy" in formatted


def test_parse_llm_response_valid_and_invalid(service):
    valid = service._parse_llm_response(
        '```json {"period_analysis":"steady","recommendation":"rest"} ```'
    )
    invalid = service._parse_llm_response("bad-json")

    assert valid["period_analysis"] == "steady"
    assert "Unable to generate analysis." in invalid["period_analysis"]


class _DummyResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


class _DummyAsyncClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, *args, **kwargs):
        return self._response


def test_call_llm_ollama_and_unknown_provider(service, monkeypatch):
    response = _DummyResponse(
        200, {"choices": [{"message": {"content": "ollama-content"}}]}
    )
    monkeypatch.setattr(
        "app.service.user_history_service.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(response),
    )
    content = asyncio.run(service._call_llm(LLMProvider.OLLAMA, "prompt"))
    assert content == "ollama-content"

    with pytest.raises(ValueError, match="Unknown provider"):
        asyncio.run(service._call_llm("invalid", "prompt"))


def test_call_llm_groq_and_gemini_require_api_keys(service, monkeypatch):
    module = __import__("app.service.user_history_service", fromlist=["llm_config"])
    module.llm_config.groq.api_key = ""
    module.llm_config.gemini.api_key = ""

    with pytest.raises(ValueError, match="Groq API key not configured"):
        asyncio.run(service._call_llm(LLMProvider.GROQ, "prompt"))

    with pytest.raises(ValueError, match="Gemini API key not configured"):
        asyncio.run(service._call_llm(LLMProvider.GEMINI, "prompt"))

    ok = _DummyResponse(200, {"choices": [{"message": {"content": "ok"}}]})
    monkeypatch.setattr(
        "app.service.user_history_service.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(ok),
    )
    module.llm_config.groq.api_key = "token"
    module.llm_config.gemini.api_key = "token"
    assert asyncio.run(service._call_llm(LLMProvider.GROQ, "prompt")) == "ok"
    assert asyncio.run(service._call_llm(LLMProvider.GEMINI, "prompt")) == "ok"
