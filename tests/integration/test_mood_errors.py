"""Integration tests for mood route exception behavior."""

from unittest.mock import AsyncMock, patch

import pytest


def test_analyze_mood_internal_error(client):
    """Current route implementation re-raises service exceptions unchanged."""
    with patch(
        "app.route.mood_analysis_routes.MoodAnalyzerService.analyze_mood",
        new=AsyncMock(side_effect=RuntimeError("analysis failed")),
    ):
        with pytest.raises(RuntimeError, match="analysis failed"):
            client.post(
                "/mood/analyze_mood",
                json={"user_id": "user01", "text": "trigger failure"},
            )
