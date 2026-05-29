import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.llm.config import LLMProvider
from app.service.wellbeing_service import WellbeingService


@pytest.fixture
def service():
    svc = WellbeingService(db=Mock())
    svc.primary_provider = LLMProvider.GEMINI
    svc.fallback_provider = LLMProvider.GROQ
    return svc


def test_get_available_activities_returns_seeded_data(service):
    result = service.get_available_activities()
    assert "activities" in result
    assert len(result["activities"]) > 0


def test_select_activity_requires_custom_activity_for_zero_id(service):
    with pytest.raises(ValueError, match="activity_id 0 requires custom_activity"):
        asyncio.run(
            service.select_activity(
                user_id="u1",
                activity_id=0,
                available_time_minutes=20,
                custom_activity=" ",
            )
        )


def test_select_activity_rejects_invalid_activity_id(service):
    with pytest.raises(ValueError, match="Invalid activity_id"):
        asyncio.run(
            service.select_activity(
                user_id="u1",
                activity_id=999,
                available_time_minutes=20,
            )
        )


def test_select_activity_success_with_custom_activity(service):
    service._generate_session = AsyncMock(
        return_value={
            "session_title": "Custom Plan",
            "session_steps": ["Step 1"],
            "estimated_duration": "20 minutes",
            "provider_used": "gemini",
            "mood_addressed": "Stress support",
        }
    )

    with patch(
        "app.service.wellbeing_service.repository.save_user_activity_selection",
        return_value=SimpleNamespace(id=7),
    ) as mock_save:
        result = asyncio.run(
            service.select_activity(
                user_id="u1",
                activity_id=0,
                available_time_minutes=20,
                mood="stressed",
                user_reason_for_mood="Workload",
                custom_activity="Yoga",
            )
        )

    assert result["activity_name"] == "Yoga"
    assert result["database_id"] == 7
    assert result["session_plan"]["provider_used"] == "gemini"
    assert mock_save.called


def test_generate_session_uses_primary_provider(service):
    service._try_llm_request = AsyncMock(
        side_effect=[
            {
                "session_title": "Primary Plan",
                "session_steps": ["Breathe"],
                "estimated_duration": "10 minutes",
                "mood_addressed": "Calm",
            }
        ]
    )

    result = asyncio.run(
        service._generate_session(
            activity_name="Meditation",
            available_time_minutes=10,
        )
    )

    assert result["session_title"] == "Primary Plan"
    assert result["provider_used"] == LLMProvider.GEMINI.value


def test_generate_session_falls_back_to_secondary_provider(service):
    service._try_llm_request = AsyncMock(
        side_effect=[
            None,
            {
                "session_title": "Fallback Plan",
                "session_steps": ["Grounding"],
                "estimated_duration": "15 minutes",
                "mood_addressed": "Anxiety support",
            },
        ]
    )

    result = asyncio.run(
        service._generate_session(
            activity_name="Meditation",
            available_time_minutes=15,
        )
    )

    assert result["session_title"] == "Fallback Plan"
    assert result["provider_used"] == LLMProvider.GROQ.value


def test_generate_session_returns_default_when_both_providers_fail(service):
    service._try_llm_request = AsyncMock(return_value=None)

    result = asyncio.run(
        service._generate_session(
            activity_name="Meditation",
            available_time_minutes=None,
        )
    )

    assert result["provider_used"] == "default"
    assert result["estimated_duration"] == "5 minutes"


def test_try_llm_request_dispatches_to_supported_provider(service):
    service._call_gemini = AsyncMock(return_value={"session_title": "x"})
    result = asyncio.run(
        service._try_llm_request(
            provider=LLMProvider.GEMINI,
            activity_name="Meditation",
            available_time=10,
        )
    )
    assert result == {"session_title": "x"}


def test_try_llm_request_returns_none_on_unknown_provider(service):
    result = asyncio.run(
        service._try_llm_request(
            provider="invalid",
            activity_name="Meditation",
            available_time=10,
        )
    )
    assert result is None


def test_try_llm_request_handles_provider_errors(service):
    service._call_groq = AsyncMock(side_effect=RuntimeError("boom"))
    result = asyncio.run(
        service._try_llm_request(
            provider=LLMProvider.GROQ,
            activity_name="Meditation",
            available_time=10,
        )
    )
    assert result is None


def test_parse_response_handles_markdown_json(service):
    result = service._parse_response(
        """```json
        {"session_title":"Plan","session_steps":["A"],"estimated_duration":"10","mood_addressed":"Calm"}
        ```"""
    )
    assert result["session_title"] == "Plan"
    assert result["session_steps"] == ["A"]


def test_parse_response_returns_none_on_invalid_json(service):
    assert service._parse_response("not-json") is None


class _DummyResponse:
    def __init__(self, status_code, payload, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

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


def test_call_gemini_success_and_failure(service, monkeypatch):
    success_response = _DummyResponse(
        200,
        {"choices": [{"message": {"content": '{"session_title":"A","session_steps":[],"estimated_duration":"5","mood_addressed":"calm"}'}}]},
    )
    fail_response = _DummyResponse(500, {}, text="error")

    monkeypatch.setattr(
        "app.service.wellbeing_service.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(success_response),
    )
    success = asyncio.run(service._call_gemini("Meditation", 5))
    assert success["session_title"] == "A"

    monkeypatch.setattr(
        "app.service.wellbeing_service.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(fail_response),
    )
    failed = asyncio.run(service._call_gemini("Meditation", 5))
    assert failed is None


def test_call_groq_success_and_failure(service, monkeypatch):
    success_response = _DummyResponse(
        200,
        {"choices": [{"message": {"content": '{"session_title":"B","session_steps":["x"],"estimated_duration":"7","mood_addressed":"focus"}'}}]},
    )
    fail_response = _DummyResponse(400, {}, text="bad")

    monkeypatch.setattr(
        "app.service.wellbeing_service.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(success_response),
    )
    success = asyncio.run(service._call_groq("Breathing", 7))
    assert success["session_title"] == "B"

    monkeypatch.setattr(
        "app.service.wellbeing_service.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(fail_response),
    )
    failed = asyncio.run(service._call_groq("Breathing", 7))
    assert failed is None


def test_call_ollama_success_and_failure(service, monkeypatch):
    success_response = _DummyResponse(
        200,
        {"choices": [{"message": {"content": '{"session_title":"C","session_steps":["y"],"estimated_duration":"8","mood_addressed":"relief"}'}}]},
    )
    fail_response = _DummyResponse(503, {}, text="down")

    monkeypatch.setattr(
        "app.service.wellbeing_service.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(success_response),
    )
    success = asyncio.run(service._call_ollama("Stretching", available_time=8))
    assert success["session_title"] == "C"

    monkeypatch.setattr(
        "app.service.wellbeing_service.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(fail_response),
    )
    failed = asyncio.run(service._call_ollama("Stretching", available_time=8))
    assert failed is None
