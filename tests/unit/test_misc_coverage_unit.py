"""Targeted unit tests to lift overall coverage past 90%.

Covers small-but-uncovered branches:
- app/database/connection.py: get_db generator (normal + exception paths)
- app/llm/config.py: invalid-provider fallback branches + get_config_for_provider
- app/main.py: root "/" redirect to "/docs"
"""

import pytest
from fastapi.testclient import TestClient

from app.database import connection as db_conn
from app.llm.config import LLMConfig, LLMProvider, OllamaConfig, GroqConfig, GeminiConfig
from app.main import app


# ---------------------------------------------------------------------------
# get_db generator
# ---------------------------------------------------------------------------

def test_get_db_yields_session_and_closes(monkeypatch):
    """get_db should yield a session and close it on generator exit."""
    closed = {"value": False}

    class FakeSession:
        def close(self):
            closed["value"] = True

    monkeypatch.setattr(db_conn, "SessionLocal", lambda: FakeSession())

    gen = db_conn.get_db()
    session = next(gen)
    assert isinstance(session, FakeSession)

    # Exhausting the generator triggers the finally block.
    with pytest.raises(StopIteration):
        next(gen)

    assert closed["value"] is True


def test_get_db_logs_and_closes_on_exception(monkeypatch):
    """If the consumer raises, get_db should propagate and still close the session."""
    closed = {"value": False}

    class FakeSession:
        def close(self):
            closed["value"] = True

    monkeypatch.setattr(db_conn, "SessionLocal", lambda: FakeSession())

    gen = db_conn.get_db()
    next(gen)  # acquire session

    with pytest.raises(RuntimeError, match="boom"):
        gen.throw(RuntimeError("boom"))

    assert closed["value"] is True


# ---------------------------------------------------------------------------
# LLMConfig fallback branches
# ---------------------------------------------------------------------------

def _make_cfg() -> LLMConfig:
    cfg = LLMConfig.__new__(LLMConfig)
    cfg.provider = "ollama"
    cfg.fallback_provider = "groq"
    cfg.ollama = OllamaConfig(base_url="http://x", model="m", timeout=1)
    cfg.groq = GroqConfig(api_key="k", base_url="http://x", model="m", timeout=1)
    cfg.gemini = GeminiConfig(api_key="k", base_url="http://x", model="m", timeout=1)
    return cfg


def test_get_primary_provider_valid():
    cfg = _make_cfg()
    cfg.provider = "groq"
    assert cfg.get_primary_provider() == LLMProvider.GROQ


def test_get_primary_provider_invalid_falls_back_to_ollama():
    cfg = _make_cfg()
    cfg.provider = "not-a-real-provider"
    assert cfg.get_primary_provider() == LLMProvider.OLLAMA


def test_get_fallback_provider_valid():
    cfg = _make_cfg()
    cfg.fallback_provider = "gemini"
    assert cfg.get_fallback_provider() == LLMProvider.GEMINI


def test_get_fallback_provider_invalid_falls_back_to_groq():
    cfg = _make_cfg()
    cfg.fallback_provider = "bogus"
    assert cfg.get_fallback_provider() == LLMProvider.GROQ


def test_get_config_for_provider_returns_correct_config():
    cfg = _make_cfg()
    assert cfg.get_config_for_provider(LLMProvider.OLLAMA) is cfg.ollama
    assert cfg.get_config_for_provider(LLMProvider.GROQ) is cfg.groq
    assert cfg.get_config_for_provider(LLMProvider.GEMINI) is cfg.gemini


def test_get_config_for_provider_unknown_raises():
    cfg = _make_cfg()
    with pytest.raises(ValueError, match="Unknown provider"):
        cfg.get_config_for_provider("nonsense")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------

def test_user_reason_for_mood_escapes_double_quotes():
    """Double quotes and backslashes in user_reason_for_mood must be escaped."""
    from app.schema.wellbeing_schema import ActivitySelectionRequest

    req = ActivitySelectionRequest(
        user_id="u1",
        activity_id=1,
        user_reason_for_mood='He said "I am fine" but path is C:\\temp',
    )
    # Backslashes escaped first, then quotes.
    assert req.user_reason_for_mood == 'He said \\"I am fine\\" but path is C:\\\\temp'


def test_user_reason_for_mood_strips_and_blank_becomes_none():
    """Whitespace-only reason text is normalized to None."""
    from app.schema.wellbeing_schema import ActivitySelectionRequest

    req = ActivitySelectionRequest(
        user_id="u1",
        activity_id=1,
        user_reason_for_mood="   \t\n  ",
    )
    assert req.user_reason_for_mood is None


def test_user_reason_for_mood_none_passes_through():
    from app.schema.wellbeing_schema import ActivitySelectionRequest

    req = ActivitySelectionRequest(user_id="u1", activity_id=1)
    assert req.user_reason_for_mood is None


def test_session_plan_coerces_numeric_duration_to_string():
    """LLMs sometimes return `estimated_duration` as int; schema must coerce it."""
    from app.schema.wellbeing_schema import SessionPlanResponse

    plan = SessionPlanResponse(
        session_title="t",
        session_steps=["a"],
        estimated_duration=40,  # int, should be coerced
        provider_used="gemini",
    )
    assert plan.estimated_duration == "40 minutes"

    plan2 = SessionPlanResponse(
        session_title="t",
        session_steps=["a"],
        estimated_duration="5 minutes",
        provider_used="gemini",
    )
    assert plan2.estimated_duration == "5 minutes"


def test_root_redirects_to_docs():
    with TestClient(app) as client:
        resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/docs"
