"""
Routes for user history and periodic mood analysis endpoints
Provides APIs to fetch user history and analyze mood trends over time
"""
import logging
from datetime import datetime, date, time
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schema.user_history_schema import (
    UserHistoryResponse,
    PeriodicMoodResponse,
    MoodHistoryItem,
    FeedbackHistoryItem,
    ActivityHistoryItem,
    MoodStatistics,
    PeriodicMoodItem
)
from app.service.user_history_service import UserHistoryService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/user",
    tags=["User History"]
)


@router.get("/{user_id}/history", response_model=UserHistoryResponse)
def get_user_history(
    user_id: str,
    db: Session = Depends(get_db)
) -> UserHistoryResponse:
    """
    Fetch complete user history

    Retrieves all historical data for a user including mood analyses,
    feedback submissions, and activity selections. This provides a
    comprehensive overview of the user's wellbeing journey.

    Path Parameters:
        user_id: Unique user identifier (alphanumeric with hyphens/underscores)

    Returns:
        UserHistoryResponse containing:
        - mood_history: List of all mood analyses
        - feedback_history: List of all feedback submissions
        - activity_history: List of all activity selections
        - Counts of each type

    Raises:
        HTTPException 400: If user_id format is invalid
        HTTPException 404: If user not found or no history available
        HTTPException 500: If database query fails

    Example:
        GET /user/user123/history
        Response:
        {
            "user_id": "user123",
            "mood_history": [...],
            "feedback_history": [...],
            "activity_history": [...],
            "total_moods": 10,
            "total_feedback": 5,
            "total_activities": 3
        }
    """
    try:
        # Validate user_id format
        if not user_id or len(user_id) < 1:
            raise HTTPException(status_code=400, detail="Invalid user_id format")

        logger.info("Fetching user history")

        service = UserHistoryService(db)
        history_data = service.get_user_history(user_id)

        # Convert database records to schema models
        mood_history = [
            MoodHistoryItem(**mood) for mood in history_data.get("mood_history", [])
        ]

        feedback_history = [
            FeedbackHistoryItem(**feedback) for feedback in history_data.get("feedback_history", [])
        ]

        activity_history = [
            ActivityHistoryItem(**activity) for activity in history_data.get("activity_history", [])
        ]

        response = UserHistoryResponse(
            user_id=user_id,
            mood_history=mood_history,
            feedback_history=feedback_history,
            activity_history=activity_history,
            total_moods=len(mood_history),
            total_feedback=len(feedback_history),
            total_activities=len(activity_history)
        )

        logger.info(
            "Successfully fetched history: "
            f"{response.total_moods} moods, {response.total_feedback} feedback, "
            f"{response.total_activities} activities"
        )

        return response

    except ValueError as e:
        logger.warning("Validation error while fetching user history: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unhandled exception while fetching user history")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user history: {str(e)}")


def _normalize_periodic_date(
    value: Union[date, datetime],
    end_of_day: bool = False
) -> datetime:
    """Normalize query date values to datetime objects.

    If the query passes a date-only value, this ensures the range
    covers the full day. If a full datetime is provided, it is preserved.
    """
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.max if end_of_day else time.min)


@router.get("/{user_id}/mood/periodic", response_model=PeriodicMoodResponse)
async def get_periodic_mood(
    user_id: str,
    from_date: Union[date, datetime] = Query(..., description="Start date for mood analysis (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    to_date: Union[date, datetime] = Query(..., description="End date for mood analysis (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    db: Session = Depends(get_db)
) -> PeriodicMoodResponse:
    """
    Fetch and analyze user's mood for a specific date range

    Retrieves all mood analyses within the specified period and generates
    statistical insights and AI-powered recommendations based on mood patterns.
    This helps track emotional wellbeing trends over time.

    Path Parameters:
        user_id: Unique user identifier (alphanumeric with hyphens/underscores)

    Query Parameters:
        from_date: Start date for the analysis period (inclusive) in ISO format
                  Examples: 2024-01-01 or 2024-01-01T00:00:00
        to_date: End date for the analysis period (inclusive) in ISO format
                Examples: 2024-01-31 or 2024-01-31T23:59:59

    Returns:
        PeriodicMoodResponse containing:
        - moods_in_period: List of mood records within the date range
        - mood_statistics: Distribution and statistics of moods
        - period_analysis: AI-generated analysis of mood patterns
        - recommendation: AI-generated personalized recommendation

    Raises:
        HTTPException 400: If user_id is invalid or date range is invalid
        HTTPException 404: If user not found or no moods in period
        HTTPException 500: If database query or LLM analysis fails

    Example:
        GET /user/user123/mood/periodic?from_date=2024-01-01&to_date=2024-01-31
        Response:
        {
            "user_id": "user123",
            "from_date": "2024-01-01T00:00:00",
            "to_date": "2024-01-31T23:59:59",
            "moods_in_period": [...],
            "mood_statistics": {
                "total_moods": 15,
                "mood_distribution": {"happy": 7, "calm": 5, "stressed": 3},
                "average_confidence": 0.87,
                "most_common_mood": "happy",
                "least_common_mood": "stressed"
            },
            "period_analysis": "Your overall mood has been positive with...",
            "recommendation": "Continue engaging in activities that boost happiness..."
        }
    """
    try:
        # Validate user_id format
        if not user_id or len(user_id) < 1:
            raise HTTPException(status_code=400, detail="Invalid user_id format")

        # Normalize date-only input values to the full day range
        from_date_dt = _normalize_periodic_date(from_date)
        to_date_dt = _normalize_periodic_date(to_date, end_of_day=True)

        # Validate date range
        if from_date_dt > to_date_dt:
            raise HTTPException(
                status_code=400,
                detail="from_date must be before or equal to to_date"
            )

        logger.info("Fetching periodic mood history")

        service = UserHistoryService(db)
        mood_data = await service.get_periodic_mood(user_id, from_date_dt, to_date_dt)

        # Convert mood records to schema models
        moods_in_period = [
            PeriodicMoodItem(**mood) for mood in mood_data.get("moods_in_period", [])
        ]

        # Create mood statistics model
        mood_stats = MoodStatistics(**mood_data.get("mood_statistics", {}))

        response = PeriodicMoodResponse(
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
            llm_provider=mood_data.get("llm_provider", "unknown"),
            moods_in_period=moods_in_period,
            mood_statistics=mood_stats,
            period_analysis=mood_data.get("period_analysis", ""),
            recommendation=mood_data.get("recommendation", "")
        )

        logger.info(
            "Successfully fetched periodic mood history: "
            f"{len(moods_in_period)} moods in period"
        )

        return response

    except ValueError as e:
        logger.warning("Validation error while fetching periodic mood: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled exception while fetching periodic mood history")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch periodic mood analysis: {str(e)}"
        )
