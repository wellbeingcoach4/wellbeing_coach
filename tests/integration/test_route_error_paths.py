"""Cover the error-handling branches in user_history and wellbeing routes."""

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Malformed JSON → 400 (global exception handler)
# ---------------------------------------------------------------------------

def test_malformed_json_returns_400_with_hint(client):
    """Body with an unterminated string should return 400, not 422."""
    bad = (
        '{"user_id":"u1","activity_id":1,'
        '"user_reason_for_mood":"unterminated string ,'  # missing closing "
        '"custom_activity":"x"}'
    )
    resp = client.post(
        "/wellbeing/select-activity",
        data=bad,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"] == "Malformed JSON in request body"
    assert "hint" in body


def test_schema_validation_still_returns_422(client):
    """A well-formed JSON body that violates the schema should still be 422."""
    resp = client.post(
        "/wellbeing/select-activity",
        json={"user_id": "", "activity_id": 1},  # invalid user_id, missing time
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /user/{user_id}/history
# ---------------------------------------------------------------------------

def test_get_user_history_value_error_returns_400(client):
    with patch(
        "app.route.user_history_routes.UserHistoryService.get_user_history",
        side_effect=ValueError("bad user"),
    ):
        resp = client.get("/user/user01/history")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "bad user"


def test_get_user_history_internal_error_returns_500(client):
    with patch(
        "app.route.user_history_routes.UserHistoryService.get_user_history",
        side_effect=RuntimeError("db down"),
    ):
        resp = client.get("/user/user01/history")
    assert resp.status_code == 500
    assert "db down" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# /user/{user_id}/mood/periodic
# ---------------------------------------------------------------------------

def test_periodic_mood_invalid_date_range_returns_400(client):
    resp = client.get(
        "/user/user01/mood/periodic",
        params={"from_date": "2025-02-01", "to_date": "2025-01-01"},
    )
    assert resp.status_code == 400
    assert "from_date must be before" in resp.json()["detail"]


def test_periodic_mood_value_error_returns_400(client):
    async def _raise(*_args, **_kwargs):
        raise ValueError("bad period")

    with patch(
        "app.route.user_history_routes.UserHistoryService.get_periodic_mood",
        side_effect=_raise,
    ):
        resp = client.get(
            "/user/user01/mood/periodic",
            params={"from_date": "2025-01-01", "to_date": "2025-01-31"},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "bad period"


def test_periodic_mood_internal_error_returns_500(client):
    async def _raise(*_args, **_kwargs):
        raise RuntimeError("llm down")

    with patch(
        "app.route.user_history_routes.UserHistoryService.get_periodic_mood",
        side_effect=_raise,
    ):
        resp = client.get(
            "/user/user01/mood/periodic",
            params={"from_date": "2025-01-01", "to_date": "2025-01-31"},
        )
    assert resp.status_code == 500
    assert "llm down" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# /wellbeing/select-activity generic-exception branch
# ---------------------------------------------------------------------------

def test_select_activity_internal_error_propagates(client):
    async def _boom(*_args, **_kwargs):
        raise RuntimeError("session generation failed")

    with patch(
        "app.route.wellbeing_routes.WellbeingService.select_activity",
        side_effect=_boom,
    ):
        # The route's `except Exception: raise` propagates; TestClient
        # re-raises with raise_server_exceptions=True (default).
        with pytest.raises(RuntimeError, match="session generation failed"):
            client.post(
                "/wellbeing/select-activity",
                json={
                    "user_id": "user01",
                    "activity_id": 1,
                    "available_time_minutes": 5,
                    "mood": "anxious",
                },
            )
