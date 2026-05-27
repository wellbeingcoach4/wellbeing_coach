import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.llm.config import LLMProvider
from app.service.mood_analyser import MoodAnalyzerService


@pytest.fixture
def service():
    svc = MoodAnalyzerService(db=Mock())
    svc.primary_provider = LLMProvider.OLLAMA
    svc.fallback_provider = LLMProvider.GROQ
    return svc


def test_analyze_mood_uses_fallback_then_saves(service):
    service._try_llm_request = AsyncMock(
        side_effect=[
            None,
            {"mood_analysed": "sad", "reason_for_mood": "negative phrasing", "confidence_score": 0.9, "provider_used": "groq"},
        ]
    )

    with patch(
        "app.service.mood_analyser.db_repository.save_mood_analysis",
        return_value=SimpleNamespace(id=10),
    ):
        result = asyncio.run(service.analyze_mood("u1", "I feel down"))

    assert result["mood_analysed"] == "sad"
    assert result["llm_provider"] == "groq"
    assert result["database_id"] == 10


def test_analyze_mood_returns_default_when_invalid_result(service):
    service._try_llm_request = AsyncMock(
        return_value={"mood_analysed": "", "reason_for_mood": ""}
    )

    with patch(
        "app.service.mood_analyser.db_repository.save_mood_analysis",
        return_value=SimpleNamespace(id=11),
    ):
        result = asyncio.run(service.analyze_mood("u1", "text"))

    assert result["mood_analysed"] == "neutral"
    assert result["llm_provider"] == "default"


def test_try_llm_request_routes_and_handles_unknown(service):
    service._call_ollama = AsyncMock(return_value={"ok": True})
    result_ollama = asyncio.run(service._try_llm_request(LLMProvider.OLLAMA, "text"))
    result_unknown = asyncio.run(service._try_llm_request("UNKNOWN", "text"))

    assert result_ollama == {"ok": True}
    assert result_unknown is None


def test_parse_llm_response_and_validation_helpers(service):
    parsed = service._parse_llm_response(
        '```json {"mood_analysed":"happy","reason_for_mood":"positive"} ```'
    )
    invalid = service._parse_llm_response("not-json")
    default = service._get_default_response()

    assert parsed["mood_analysed"] == "happy"
    assert invalid is None
    assert service._is_valid_response(parsed) is True
    assert service._is_valid_response({"mood_analysed": "", "reason_for_mood": ""}) is False
    assert default["provider_used"] == "default"


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


def test_call_ollama_success_and_failure(service, monkeypatch):
    ok = _DummyResponse(
        200,
        {"choices": [{"message": {"content": '{"mood_analysed":"happy","reason_for_mood":"positive"}'}}]},
    )
    bad = _DummyResponse(500, {})

    monkeypatch.setattr(
        "app.service.mood_analyser.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(ok),
    )
    parsed = asyncio.run(service._call_ollama("great day"))
    assert parsed["provider_used"] == "ollama"

    monkeypatch.setattr(
        "app.service.mood_analyser.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(bad),
    )
    failed = asyncio.run(service._call_ollama("great day"))
    assert failed is None


def test_call_groq_handles_api_key_and_status(service, monkeypatch):
    service_module = __import__("app.service.mood_analyser", fromlist=["llm_config"])
    service_module.llm_config.groq.api_key = "token"

    ok = _DummyResponse(
        200,
        {"choices": [{"message": {"content": '{"mood_analysed":"calm","reason_for_mood":"balanced"}'}}]},
    )
    fail = _DummyResponse(401, {}, text="unauthorized")

    monkeypatch.setattr(
        "app.service.mood_analyser.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(ok),
    )
    parsed = asyncio.run(service._call_groq("text"))
    assert parsed["provider_used"] == "groq"

    monkeypatch.setattr(
        "app.service.mood_analyser.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(fail),
    )
    failed = asyncio.run(service._call_groq("text"))
    assert failed is None

    service_module.llm_config.groq.api_key = ""
    no_key = asyncio.run(service._call_groq("text"))
    assert no_key is None


def test_call_gemini_handles_api_key_and_status(service, monkeypatch):
    service_module = __import__("app.service.mood_analyser", fromlist=["llm_config"])
    service_module.llm_config.gemini.api_key = "token"

    ok = _DummyResponse(
        200,
        {"choices": [{"message": {"content": '{"mood_analysed":"neutral","reason_for_mood":"mixed"}'}}]},
    )
    fail = _DummyResponse(429, {}, text="throttle")

    monkeypatch.setattr(
        "app.service.mood_analyser.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(ok),
    )
    parsed = asyncio.run(service._call_gemini("text"))
    assert parsed["provider_used"] == "gemini"

    monkeypatch.setattr(
        "app.service.mood_analyser.httpx.AsyncClient",
        lambda timeout: _DummyAsyncClient(fail),
    )
    failed = asyncio.run(service._call_gemini("text"))
    assert failed is None

    service_module.llm_config.gemini.api_key = ""
    no_key = asyncio.run(service._call_gemini("text"))
    assert no_key is None
