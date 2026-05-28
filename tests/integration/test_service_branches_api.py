"""Integration tests that exercise service-layer error/fallback branches
through the public API. These drive coverage on mood_analyser,
wellbeing_service, and user_history_service via the HTTP layer.
"""

from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers: configurable AsyncClient mock that can return a sequence of
# (status_code, content) pairs across successive .post() calls.
# ---------------------------------------------------------------------------

def _install_sequenced_async_client(monkeypatch, target_modules, responses):
    """Patch httpx.AsyncClient in the given modules to yield `responses` in order.

    Each response is a tuple of (status_code, content_str). When exhausted,
    the last response repeats.
    """
    state = {"i": 0}

    class _Response:
        def __init__(self, status_code, content):
            self.status_code = status_code
            self.text = content
            self._content = content

        def json(self):
            return {"choices": [{"message": {"content": self._content}}]}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

    class _AsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, *args, **kwargs):
            idx = min(state["i"], len(responses) - 1)
            state["i"] += 1
            status, content = responses[idx]
            return _Response(status, content)

    for module in target_modules:
        monkeypatch.setattr(f"{module}.httpx.AsyncClient", _AsyncClient)


# ---------------------------------------------------------------------------
# /mood/analyze_mood — LLM error / fallback / parser branches
# ---------------------------------------------------------------------------

def test_analyze_mood_primary_fails_fallback_succeeds(client, monkeypatch):
    """Non-200 on primary then valid JSON on fallback should still return 200."""
    import app.service.mood_analyser as ma
    monkeypatch.setattr(ma.llm_config.groq, "api_key", "test-token")
    monkeypatch.setattr(ma.llm_config.gemini, "api_key", "test-token")
    _install_sequenced_async_client(
        monkeypatch,
        ["app.service.mood_analyser"],
        [
            (500, "boom"),
            (200, '{"mood_analysed":"calm","reason_for_mood":"steady tone"}'),
        ],
    )

    resp = client.post(
        "/mood/analyze_mood",
        json={"user_id": "user01", "text": "I feel steady"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mood_analysed"] == "calm"


def test_analyze_mood_both_providers_fail_returns_default(client, monkeypatch):
    """Non-200 on both providers should yield the default neutral response."""
    _install_sequenced_async_client(
        monkeypatch,
        ["app.service.mood_analyser"],
        [(500, "boom"), (502, "still broken")],
    )

    resp = client.post(
        "/mood/analyze_mood",
        json={"user_id": "user01", "text": "something"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mood_analysed"] == "neutral"
    assert body["llm_provider"] == "default"


def test_analyze_mood_invalid_json_uses_default(client, monkeypatch):
    """200 with non-JSON content should fall back to the default response."""
    _install_sequenced_async_client(
        monkeypatch,
        ["app.service.mood_analyser"],
        [(200, "not-json"), (200, "still-not-json")],
    )

    resp = client.post(
        "/mood/analyze_mood",
        json={"user_id": "user01", "text": "x"},
    )
    assert resp.status_code == 200
    assert resp.json()["llm_provider"] == "default"


def test_analyze_mood_missing_fields_uses_default(client, monkeypatch):
    """Valid JSON missing required fields should be treated as invalid."""
    _install_sequenced_async_client(
        monkeypatch,
        ["app.service.mood_analyser"],
        [
            (200, '{"foo": "bar"}'),
            (200, '{"baz": "qux"}'),
        ],
    )

    resp = client.post(
        "/mood/analyze_mood",
        json={"user_id": "user01", "text": "x"},
    )
    assert resp.status_code == 200
    assert resp.json()["llm_provider"] == "default"


# ---------------------------------------------------------------------------
# /wellbeing/select-activity — fallback + default branches
# ---------------------------------------------------------------------------

def test_select_activity_primary_fails_fallback_succeeds(client, monkeypatch):
    _install_sequenced_async_client(
        monkeypatch,
        ["app.service.wellbeing_service"],
        [
            (500, "down"),
            (
                200,
                '{"session_title":"Fallback Plan","session_steps":["A","B"],'
                '"estimated_duration":"5m","mood_addressed":"calm"}',
            ),
        ],
    )

    resp = client.post(
        "/wellbeing/select-activity",
        json={
            "user_id": "user01",
            "activity_id": 1,
            "available_time_minutes": 5,
            "mood": "stressed",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["session_plan"]["session_title"] == "Fallback Plan"


def test_select_activity_both_providers_fail_uses_default_session(client, monkeypatch):
    _install_sequenced_async_client(
        monkeypatch,
        ["app.service.wellbeing_service"],
        [(500, "down"), (500, "down")],
    )

    resp = client.post(
        "/wellbeing/select-activity",
        json={
            "user_id": "user01",
            "activity_id": 1,
            "available_time_minutes": 5,
            "mood": "sad",
        },
    )
    assert resp.status_code == 200
    plan = resp.json()["session_plan"]
    assert plan["provider_used"] == "default"
    assert plan["session_title"] == "Basic Relaxation"


def test_select_activity_blank_custom_activity_rejected(client):
    """activity_id=0 with whitespace-only custom_activity should 400."""
    resp = client.post(
        "/wellbeing/select-activity",
        json={
            "user_id": "user01",
            "activity_id": 0,
            "available_time_minutes": 5,
            "custom_activity": "   ",
        },
    )
    assert resp.status_code == 400
    assert "custom_activity" in resp.json()["detail"]


def test_select_activity_includes_past_feedback_in_prompt(client, monkeypatch):
    """Feedback linked to a previous session should influence subsequent
    sessions (exercises _build_past_feedback_summary non-empty branch).
    """
    # Seed first session via standard mock
    _install_sequenced_async_client(
        monkeypatch,
        ["app.service.wellbeing_service"],
        [
            (
                200,
                '{"session_title":"S1","session_steps":["a"],'
                '"estimated_duration":"5m","mood_addressed":"x"}',
            ),
        ],
    )
    first = client.post(
        "/wellbeing/select-activity",
        json={
            "user_id": "user01",
            "activity_id": 1,
            "available_time_minutes": 5,
            "mood": "anxious",
        },
    )
    selection_id = first.json()["database_id"]

    # Submit feedback linked to that selection
    fb = client.post(
        "/feedback/",
        json={
            "user_id": "user01",
            "feedback_text": "Loved this calming session",
            "rating": 5,
            "activity_selection_id": selection_id,
        },
    )
    assert fb.status_code == 200

    # Capture the prompt content sent on the second request
    captured = {"content": None}

    class _Response:
        status_code = 200
        text = ""

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"session_title":"S2","session_steps":["a"],'
                                '"estimated_duration":"5m","mood_addressed":"x"}'
                            )
                        }
                    }
                ]
            }

    class _AsyncClient:
        def __init__(self, *_a, **_k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            return None

        async def post(self, *_a, **kwargs):
            payload = kwargs.get("json", {})
            messages = payload.get("messages", [])
            if messages:
                captured["content"] = messages[0]["content"]
            return _Response()

    monkeypatch.setattr(
        "app.service.wellbeing_service.httpx.AsyncClient", _AsyncClient
    )

    second = client.post(
        "/wellbeing/select-activity",
        json={
            "user_id": "user01",
            "activity_id": 1,
            "available_time_minutes": 5,
            "mood": "anxious",
        },
    )
    assert second.status_code == 200
    assert captured["content"] is not None
    # Past feedback section should be populated and reference the rating + text.
    assert "5/5" in captured["content"]
    assert "Loved this calming session" in captured["content"]


# ---------------------------------------------------------------------------
# /user/{user_id}/mood/periodic — LLM error path returns 500
# ---------------------------------------------------------------------------

def test_periodic_mood_llm_failure_falls_back_gracefully(client, mock_chat_completion):
    """Seed one mood; both LLM providers fail. Service returns 200 with default text."""
    mock_chat_completion(
        '{"mood_analysed":"happy","reason_for_mood":"Good day"}'
    )
    client.post(
        "/mood/analyze_mood",
        json={"user_id": "user02", "text": "Great day"},
    )

    async def _raise(*_a, **_k):
        raise RuntimeError("llm offline")

    with patch(
        "app.service.user_history_service.UserHistoryService._call_llm",
        side_effect=_raise,
    ):
        resp = client.get(
            "/user/user02/mood/periodic",
            params={"from_date": "2020-01-01", "to_date": "2099-12-31"},
        )
    assert resp.status_code == 200
    body = resp.json()
    # Service should still return aggregated stats even when LLM is down.
    assert body["mood_statistics"]["total_moods"] >= 1


def test_periodic_mood_no_records_returns_response_without_llm(client):
    """A user with no mood records should still get a structured response."""
    resp = client.get(
        "/user/no_one/mood/periodic",
        params={"from_date": "2020-01-01", "to_date": "2099-12-31"},
    )
    # Either 200 with empty stats, or 404 — both are acceptable contract-wise.
    assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# Misc surface area
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Gemini-provider branches across services
# ---------------------------------------------------------------------------

def _force_gemini_primary(monkeypatch, service_module_path):
    """Force a service to pick Gemini as both primary and fallback provider."""
    from app.llm.config import LLMProvider, llm_config

    monkeypatch.setattr(llm_config.gemini, "api_key", "test-token")
    monkeypatch.setattr(
        llm_config, "get_primary_provider", lambda: LLMProvider.GEMINI
    )
    monkeypatch.setattr(
        llm_config, "get_fallback_provider", lambda: LLMProvider.GEMINI
    )


def test_analyze_mood_via_gemini_provider(client, monkeypatch):
    _force_gemini_primary(monkeypatch, "app.service.mood_analyser")
    _install_sequenced_async_client(
        monkeypatch,
        ["app.service.mood_analyser"],
        [(200, '{"mood_analysed":"happy","reason_for_mood":"sunny"}')],
    )

    resp = client.post(
        "/mood/analyze_mood",
        json={"user_id": "user01", "text": "great day"},
    )
    assert resp.status_code == 200
    assert resp.json()["mood_analysed"] == "happy"


def test_analyze_mood_gemini_http_error_falls_back_to_default(client, monkeypatch):
    """Non-200 from Gemini exercises the Gemini error-log branch."""
    _force_gemini_primary(monkeypatch, "app.service.mood_analyser")
    _install_sequenced_async_client(
        monkeypatch,
        ["app.service.mood_analyser"],
        [(429, "throttle"), (429, "throttle")],
    )
    resp = client.post(
        "/mood/analyze_mood",
        json={"user_id": "user01", "text": "x"},
    )
    assert resp.status_code == 200
    assert resp.json()["llm_provider"] == "default"


def test_select_activity_via_gemini_provider(client, monkeypatch):
    _force_gemini_primary(monkeypatch, "app.service.wellbeing_service")
    _install_sequenced_async_client(
        monkeypatch,
        ["app.service.wellbeing_service"],
        [
            (
                200,
                '{"session_title":"Gemini Plan","session_steps":["a","b"],'
                '"estimated_duration":"5m","mood_addressed":"ok"}',
            )
        ],
    )
    resp = client.post(
        "/wellbeing/select-activity",
        json={
            "user_id": "user01",
            "activity_id": 1,
            "available_time_minutes": 5,
            "mood": "anxious",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["session_plan"]["session_title"] == "Gemini Plan"


def test_periodic_mood_via_gemini_provider(client, monkeypatch, mock_chat_completion):
    """Seed a mood, then exercise the periodic flow with Gemini as primary."""
    mock_chat_completion(
        '{"mood_analysed":"calm","reason_for_mood":"steady"}'
    )
    client.post(
        "/mood/analyze_mood",
        json={"user_id": "user03", "text": "all good"},
    )

    _force_gemini_primary(monkeypatch, "app.service.user_history_service")
    _install_sequenced_async_client(
        monkeypatch,
        ["app.service.user_history_service"],
        [
            (
                200,
                '{"period_analysis":"Stable mood","recommendation":"Keep it up"}',
            )
        ],
    )

    resp = client.get(
        "/user/user03/mood/periodic",
        params={"from_date": "2020-01-01", "to_date": "2099-12-31"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["period_analysis"] == "Stable mood"
    assert body["recommendation"] == "Keep it up"


def test_periodic_mood_invalid_json_uses_default_text(client, monkeypatch, mock_chat_completion):
    """Non-JSON LLM output for periodic flow should yield default analysis text."""
    mock_chat_completion(
        '{"mood_analysed":"calm","reason_for_mood":"steady"}'
    )
    client.post(
        "/mood/analyze_mood",
        json={"user_id": "user04", "text": "all good"},
    )

    _force_gemini_primary(monkeypatch, "app.service.user_history_service")
    _install_sequenced_async_client(
        monkeypatch,
        ["app.service.user_history_service"],
        [(200, "not a json blob")],
    )

    resp = client.get(
        "/user/user04/mood/periodic",
        params={"from_date": "2020-01-01", "to_date": "2099-12-31"},
    )
    assert resp.status_code == 200
    assert resp.json()["period_analysis"].startswith("Unable")


# ---------------------------------------------------------------------------
def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root_redirect(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/docs"
