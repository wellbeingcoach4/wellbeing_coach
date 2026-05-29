"""
Test module for user history APIs
Tests the user history retrieval and periodic mood analysis endpoints
"""
import pytest
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch, AsyncMock

from app.service.user_history_service import UserHistoryService
from app.route.user_history_routes import _normalize_periodic_date
from app.schema.user_history_schema import (
    UserHistoryResponse,
    PeriodicMoodResponse,
    MoodHistoryItem,
    FeedbackHistoryItem
)


class TestUserHistoryService:
    """Test suite for UserHistoryService"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock(spec=Session)

    @pytest.fixture
    def user_history_service(self, mock_db):
        """Create a UserHistoryService instance with mocked db"""
        return UserHistoryService(db=mock_db)

    def test_get_user_history_success(self, user_history_service, mock_db):
        """
        Test successful retrieval of user history

        Verifies that the service correctly aggregates mood, feedback, and activity data
        from the repository layer.
        """
        user_id = "test_user_123"

        # Mock repository responses
        mock_moods = [
            {
                "id": 1,
                "user_id": user_id,
                "mood_analysed": "happy",
                "reason_for_mood": "Had a great day",
                "confidence_score": 0.95,
                "llm_provider": "ollama",
                "created_at": datetime.now(),
                "input_text": "I'm feeling great"
            }
        ]

        mock_feedback = [
            {
                "id": 1,
                "user_id": user_id,
                "feedback_text": "Great experience",
                "rating": 5,
                "created_at": datetime.now()
            }
        ]

        mock_activities = []

        # Patch repository methods
        with patch('app.service.user_history_service.db_repository.get_user_moods', return_value=mock_moods), \
                patch('app.service.user_history_service.db_repository.get_user_feedback', return_value=mock_feedback), \
                patch('app.service.user_history_service.db_repository.get_user_activities', return_value=mock_activities):

            result = user_history_service.get_user_history(user_id)

        # Assertions
        assert result["user_id"] == user_id
        assert result["total_moods"] == 1
        assert result["total_feedback"] == 1
        assert result["total_activities"] == 0
        assert len(result["mood_history"]) == 1
        assert result["mood_history"][0]["mood_analysed"] == "happy"

    def test_get_user_history_empty(self, user_history_service):
        """
        Test retrieval of user history when no records exist

        Verifies that the service returns empty lists without errors.
        """
        user_id = "nonexistent_user"

        # Patch repository methods to return empty lists
        with patch('app.service.user_history_service.db_repository.get_user_moods', return_value=[]), \
                patch('app.service.user_history_service.db_repository.get_user_feedback', return_value=[]), \
                patch('app.service.user_history_service.db_repository.get_user_activities', return_value=[]):

            result = user_history_service.get_user_history(user_id)

        # Assertions
        assert result["user_id"] == user_id
        assert result["total_moods"] == 0
        assert result["total_feedback"] == 0
        assert result["total_activities"] == 0
        assert result["mood_history"] == []
        assert result["feedback_history"] == []
        assert result["activity_history"] == []

    @pytest.mark.asyncio
    async def test_get_periodic_mood_valid_range(self, user_history_service):
        """
        Test periodic mood retrieval with valid date range

        Verifies that the service correctly:
        1. Validates the date range
        2. Retrieves mood data for the period
        3. Calculates statistics
        4. Generates AI analysis
        """
        user_id = "test_user_123"
        from_date = datetime(2024, 1, 1)
        to_date = datetime(2024, 1, 31)

        mock_moods = [
            {
                "id": 1,
                "user_id": user_id,
                "mood_analysed": "happy",
                "reason_for_mood": "Had a great day",
                "confidence_score": 0.95,
                "llm_provider": "ollama",
                "created_at": datetime(2024, 1, 15),
                "input_text": "I'm feeling great"
            },
            {
                "id": 2,
                "user_id": user_id,
                "mood_analysed": "happy",
                "reason_for_mood": "Completed project",
                "confidence_score": 0.90,
                "llm_provider": "ollama",
                "created_at": datetime(2024, 1, 20),
                "input_text": "Finished the project"
            }
        ]

        mock_ai_response = {
            "period_analysis": "You had a positive month overall",
            "recommendation": "Continue engaging in activities that make you happy"
        }

        # Patch repository and LLM methods
        with patch('app.service.user_history_service.db_repository.get_user_moods_in_period', return_value=mock_moods), \
                patch.object(user_history_service, '_generate_mood_analysis', return_value=mock_ai_response):

            result = await user_history_service.get_periodic_mood(user_id, from_date, to_date)

        # Assertions
        assert result["user_id"] == user_id
        assert len(result["moods_in_period"]) == 2
        assert result["mood_statistics"]["total_moods"] == 2
        assert result["mood_statistics"]["most_common_mood"] == "happy"
        assert result["mood_statistics"]["average_confidence"] > 0
        assert "period_analysis" in result
        assert "recommendation" in result
        assert all(
            "llm_provider" in mood for mood in result["moods_in_period"])

    @pytest.mark.asyncio
    async def test_get_periodic_mood_invalid_date_range(self, user_history_service):
        """
        Test periodic mood retrieval with invalid date range

        Verifies that the service raises ValueError when from_date > to_date.
        """
        user_id = "test_user_123"
        from_date = datetime(2024, 1, 31)
        to_date = datetime(2024, 1, 1)

        with pytest.raises(ValueError, match="from_date must be before or equal to to_date"):
            await user_history_service.get_periodic_mood(user_id, from_date, to_date)

    def test_normalize_periodic_date_range_date_only(self):
        """
        Test normalization of date-only periodic mood query parameters

        Verifies that a date-only to_date is expanded to the end of the day.
        """
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)

        normalized_start = _normalize_periodic_date(start_date)
        normalized_end = _normalize_periodic_date(end_date, end_of_day=True)

        assert normalized_start == datetime(2024, 1, 15, 0, 0, 0)
        assert normalized_end == datetime(2024, 1, 15, 23, 59, 59, 999999)

    def test_calculate_mood_statistics(self, user_history_service):
        """
        Test mood statistics calculation

        Verifies that the service correctly calculates:
        - Mood distribution
        - Average confidence score
        - Most and least common moods
        """
        moods = [
            {"mood_analysed": "happy", "confidence_score": 0.95},
            {"mood_analysed": "happy", "confidence_score": 0.90},
            {"mood_analysed": "calm", "confidence_score": 0.85},
            {"mood_analysed": "stressed", "confidence_score": 0.70},
        ]

        stats = user_history_service._calculate_mood_statistics(moods)

        # Assertions
        assert stats["total_moods"] == 4
        assert stats["mood_distribution"]["happy"] == 2
        assert stats["mood_distribution"]["calm"] == 1
        assert stats["mood_distribution"]["stressed"] == 1
        assert stats["most_common_mood"] == "happy"
        assert stats["least_common_mood"] in ["calm", "stressed"]
        assert 0.75 < stats["average_confidence"] < 0.90

    def test_calculate_mood_statistics_empty(self, user_history_service):
        """
        Test mood statistics calculation with empty mood list

        Verifies that the service returns sensible defaults for empty data.
        """
        moods = []

        stats = user_history_service._calculate_mood_statistics(moods)

        # Assertions
        assert stats["total_moods"] == 0
        assert stats["mood_distribution"] == {}
        assert stats["average_confidence"] == 0.0
        assert stats["most_common_mood"] is None
        assert stats["least_common_mood"] is None

    def test_format_mood_data_for_llm(self, user_history_service):
        """
        Test formatting of mood data for LLM input

        Verifies that the service correctly formats mood data into
        a readable string for LLM analysis.
        """
        moods = [
            {
                "created_at": "2024-01-15",
                "mood_analysed": "happy",
                "confidence_score": 0.95
            },
            {
                "created_at": "2024-01-20",
                "mood_analysed": "calm",
                "confidence_score": 0.85
            }
        ]

        formatted = user_history_service._format_mood_data_for_llm(moods)

        # Assertions
        assert "2024-01-15" in formatted
        assert "happy" in formatted
        assert "0.95" in formatted
        assert "\n" in formatted

    def test_format_mood_data_for_llm_empty(self, user_history_service):
        """
        Test formatting of empty mood data for LLM input

        Verifies that the service returns a default message for empty data.
        """
        formatted = user_history_service._format_mood_data_for_llm([])

        assert "No mood data available" in formatted


class TestUserHistorySchemas:
    """Test suite for user history schema validation"""

    def test_user_history_response_schema(self):
        """
        Test UserHistoryResponse schema validation

        Verifies that the schema correctly validates user history data.
        """
        history_data = {
            "user_id": "test_user",
            "mood_history": [],
            "feedback_history": [],
            "activity_history": [],
            "total_moods": 0,
            "total_feedback": 0,
            "total_activities": 0
        }

        response = UserHistoryResponse(**history_data)

        assert response.user_id == "test_user"
        assert response.total_moods == 0

    def test_periodic_mood_response_schema(self):
        """
        Test PeriodicMoodResponse schema validation

        Verifies that the schema correctly validates periodic mood data.
        """
        periodic_data = {
            "user_id": "test_user",
            "from_date": datetime(2024, 1, 1),
            "to_date": datetime(2024, 1, 31),
            "llm_provider": "ollama",
            "moods_in_period": [],
            "mood_statistics": {
                "total_moods": 0,
                "mood_distribution": {},
                "average_confidence": 0.0,
                "most_common_mood": None,
                "least_common_mood": None
            },
            "period_analysis": "Test analysis",
            "recommendation": "Test recommendation"
        }

        response = PeriodicMoodResponse(**periodic_data)

        assert response.user_id == "test_user"
        assert response.mood_statistics.total_moods == 0
