"""Extra unit tests to push coverage to 98%+.

Targets the remaining uncovered branches in:
- app/service/mood_analyser.py  (LLM error paths, parser edge cases, both-providers-fail)
- app/service/wellbeing_service.py (feedback summary exception + truncation)
- app/service/user_history_service.py (provider None / unknown / parser exception)
- app/main.py lifespan startup/shutdown failure branches
- app/database/models.py __repr__
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.database.models import MoodAnalysis
from app.llm.config import LLMProvider
from app.service.mood_analyser import MoodAnalyzerService
from app.service.user_history_service import UserHistoryService
from app.service.wellbeing_service import WellbeingService


# ---------------------------------------------------------------------------
# mood_analyser: cover remaining error/edge branches
# ---------------------------------------------------------------------------

@pytest.fixture
def mood_service():
    svc = MoodAnalyzerService(db=Mock())
    svc.primary_provider = LLMProvider.OLLAMA
    svc.fallback_provider = LLMProvider.GROQ
    return svc


def test_analyze_mood_returns_default_when_both_providers_return_none(mood_service):
    """Both primary and fallback returning None should hit the default branch (lines 67-69)."""
    mood_service._try_llm_request = AsyncMock(side_effect=[None, None])
    with patch(
        "app.service.mood_analyser.db_repository.save_mood_analysis",
        return_value=SimpleNamespace(id=99),
    ):
        result = asyncio.run(mood_service.analyze_mood("u1", "any text"))
    assert result["mood_analysed"] == "neutral"
    assert result["llm_provider"] == "default"


def test_try_llm_request_routes_to_groq_and_gemini(mood_service):
    """Cover the GROQ and GEMINI branches in _try_llm_request (lines 113, 115)."""
    mood_service._call_groq = AsyncMock(return_value={"groq": True})
    mood_service._call_gemini = AsyncMock(return_value={"gemini": True})
    assert asyncio.run(mood_service._try_llm_request(LLMProvider.GROQ, "t")) == {"groq": True}
    assert asyncio.run(mood_service._try_llm_request(LLMProvider.GEMINI, "t")) == {"gemini": True}


def test_try_llm_request_swallows_provider_exception(mood_service):
    """A provider raising an exception should return None (lines 119-121)."""
    mood_service._call_ollama = AsyncMock(side_effect=RuntimeError("boom"))
    assert asyncio.run(mood_service._try_llm_request(LLMProvider.OLLAMA, "t")) is None


def _make_raising_async_client(exc):
    class _Raises:
        def __init__(self, *_a, **_k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            return None

        async def post(self, *_a, **_k):
            raise exc

    return _Raises


def test_call_ollama_exception_branch(mood_service, monkeypatch):
    """httpx raising inside _call_ollama hits the outer except (lines 159-161)."""
    monkeypatch.setattr(
        "app.service.mood_analyser.httpx.AsyncClient",
        _make_raising_async_client(RuntimeError("net")),
    )
    assert asyncio.run(mood_service._call_ollama("t")) is None


def test_call_groq_exception_branch(mood_service, monkeypatch):
    """httpx raising inside _call_groq hits the outer except (lines 200-202)."""
    import app.service.mood_analyser as ma
    ma.llm_config.groq.api_key = "token"
    monkeypatch.setattr(
        "app.service.mood_analyser.httpx.AsyncClient",
        _make_raising_async_client(RuntimeError("net")),
    )
    assert asyncio.run(mood_service._call_groq("t")) is None


def test_call_gemini_exception_branch(mood_service, monkeypatch):
    """httpx raising inside _call_gemini hits the outer except (lines 247-249)."""
    import app.service.mood_analyser as ma
    ma.llm_config.gemini.api_key = "token"
    monkeypatch.setattr(
        "app.service.mood_analyser.httpx.AsyncClient",
        _make_raising_async_client(RuntimeError("net")),
    )
    assert asyncio.run(mood_service._call_gemini("t")) is None


def test_parse_llm_response_missing_required_fields(mood_service):
    """Valid JSON but missing fields returns None (lines 280-283)."""
    assert mood_service._parse_llm_response('{"foo": "bar"}') is None


def test_parse_llm_response_unexpected_exception(mood_service):
    """A non-string argument raises an unexpected exception (lines 302-305)."""
    assert mood_service._parse_llm_response(12345) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# wellbeing_service: feedback summary edge branches
# ---------------------------------------------------------------------------

def test_build_past_feedback_summary_swallows_repository_error():
    """Repository error should be caught and yield 'No prior feedback' (lines 231-233)."""
    svc = WellbeingService(db=Mock())
    with patch(
        "app.service.wellbeing_service.repository.get_recent_feedback_for_prompt",
        side_effect=RuntimeError("db down"),
    ):
        assert svc._build_past_feedback_summary("u1") == "No prior feedback"


def test_build_past_feedback_summary_truncates_long_text():
    """Feedback longer than 160 chars should be truncated (line 245)."""
    svc = WellbeingService(db=Mock())
    long_text = "x" * 300
    with patch(
        "app.service.wellbeing_service.repository.get_recent_feedback_for_prompt",
        return_value=[{
            "rating": 5,
            "feedback_text": long_text,
            "activity_name": "Breathing",
            "session_title": "t",
        }],
    ):
        summary = svc._build_past_feedback_summary("u1")
    assert "..." in summary
    assert "Breathing" in summary
    assert "5/5" in summary


# ---------------------------------------------------------------------------
# user_history_service: provider edge branches in _call_llm_provider
# ---------------------------------------------------------------------------

def test_call_llm_provider_none_raises_value_error():
    """A None provider should raise ValueError (line 341)."""
    svc = UserHistoryService(db=Mock())
    with pytest.raises(ValueError, match="No LLM provider available"):
        asyncio.run(svc._call_llm(None, "prompt"))


def test_parse_periodic_response_unexpected_exception_returns_default():
    """Non-string response triggers the generic except branch (lines 448-451)."""
    svc = UserHistoryService(db=Mock())
    result = svc._parse_llm_response(None)  # type: ignore[arg-type]
    assert result["period_analysis"].startswith("Unable")
    assert result["recommendation"].startswith("Please try again")


# ---------------------------------------------------------------------------
# main.py lifespan failure branches
# ---------------------------------------------------------------------------

def test_lifespan_startup_failure_propagates(monkeypatch):
    """init_db raising during startup should bubble up (lines 33-35)."""
    import app.main as main_module

    monkeypatch.setattr(main_module, "init_db", lambda: (_ for _ in ()).throw(RuntimeError("init failed")))

    async def _run():
        async with main_module.lifespan(main_module.app):
            pass

    with pytest.raises(RuntimeError, match="init failed"):
        asyncio.run(_run())


def test_lifespan_shutdown_failure_propagates(monkeypatch):
    """close_db raising during shutdown should bubble up (lines 43-45)."""
    import app.main as main_module

    monkeypatch.setattr(main_module, "init_db", lambda: None)
    monkeypatch.setattr(main_module, "close_db", lambda: (_ for _ in ()).throw(RuntimeError("close failed")))

    async def _run():
        async with main_module.lifespan(main_module.app):
            pass

    with pytest.raises(RuntimeError, match="close failed"):
        asyncio.run(_run())


# ---------------------------------------------------------------------------
# models.__repr__
# ---------------------------------------------------------------------------

def test_mood_analysis_repr():
    record = MoodAnalysis(
        user_id="u1",
        input_text="hi",
        mood_analysed="happy",
        reason_for_mood="r",
        confidence_score=0.9,
        llm_provider="ollama",
    )
    text = repr(record)
    assert "u1" in text and "happy" in text and "ollama" in text
