"""
Database Repository Layer
Handles all database operations for mood analysis, feedback, activities, and history queries
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.models import MoodAnalysis, UserActivitySelection, UserFeedback

logger = logging.getLogger(__name__)


def save_mood_analysis(
    db: Session,
    user_id: str,
    input_text: str,
    mood_analysed: str,
    reason_for_mood: str,
    confidence_score: Optional[float],
    llm_provider: str
) -> Optional[MoodAnalysis]:
    """
    Save mood analysis result to database

    Args:
        db: Database session
        user_id: User identifier
        input_text: Original input text
        mood_analysed: Analyzed mood
        reason_for_mood: Reason for the mood
        confidence_score: Confidence score (0-1)
        llm_provider: Provider used for analysis

    Returns:
        Created MoodAnalysis record or None if failed
    """
    try:
        mood_record = MoodAnalysis(
            user_id=user_id,
            input_text=input_text,
            mood_analysed=mood_analysed,
            reason_for_mood=reason_for_mood,
            confidence_score=confidence_score,
            llm_provider=llm_provider
        )

        db.add(mood_record)
        db.commit()
        db.refresh(mood_record)

        logger.info("Mood analysis saved with ID=%s", mood_record.id)
        return mood_record

    except Exception:
        logger.exception("Failed to save mood analysis")
        db.rollback()
        return None

def save_user_activity_selection(
    db,
    user_id,
    activity_id,
    activity_name,
    available_time_minutes,
    ai_session_title,
    ai_session_steps,
    ai_estimated_duration,
    llm_provider,
    user_reason_for_mood=None,
    custom_activity=None
):
    try:

        record = UserActivitySelection(

        user_id=user_id,

        activity_id=activity_id,

        activity_name=activity_name,

        available_time_minutes=available_time_minutes,

        ai_session_title=ai_session_title,

        ai_session_steps=ai_session_steps,

        ai_estimated_duration=ai_estimated_duration,

        llm_provider=llm_provider,
        user_reason_for_mood=user_reason_for_mood,
        custom_activity=custom_activity
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        logger.info("User activity selection saved with ID=%s", record.id)
        return record

    except Exception:
        logger.exception("Failed to save user activity selection")
        db.rollback()
        return None


def save_feedback(
    db: Session,
    user_id: str,
    feedback_text: str,
    rating: Optional[int] = None,
    activity_selection_id: Optional[int] = None,
) -> Optional[UserFeedback]:
    """
    Save user feedback to database
    """
    try:
        feedback = UserFeedback(
            user_id=user_id,
            feedback_text=feedback_text,
            rating=rating,
            activity_selection_id=activity_selection_id,
        )

        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        logger.info("User feedback saved with ID=%s", feedback.id)
        return feedback

    except Exception:
        logger.exception("Failed to save user feedback")
        db.rollback()
        return None


# ============================================================================
# Feedback-driven personalization helpers
# ============================================================================

def get_recent_feedback_for_prompt(
    db: Session,
    user_id: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Return a compact list of the user's most recent feedback entries joined
    with the activity they referred to (if any). Used to personalize future
    session generation.
    """
    try:
        rows = (
            db.query(
                UserFeedback.rating,
                UserFeedback.feedback_text,
                UserFeedback.created_at,
                UserActivitySelection.activity_name,
                UserActivitySelection.ai_session_title,
            )
            .outerjoin(
                UserActivitySelection,
                UserFeedback.activity_selection_id == UserActivitySelection.id,
            )
            .filter(UserFeedback.user_id == user_id)
            .order_by(UserFeedback.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "rating": row.rating,
                "feedback_text": row.feedback_text,
                "activity_name": row.activity_name,
                "session_title": row.ai_session_title,
            }
            for row in rows
        ]
    except Exception:
        logger.exception("Failed to fetch recent feedback for personalization")
        return []


# ============================================================================
# User History and Periodic Query Methods
# ============================================================================

def get_user_moods(
    db: Session,
    user_id: str
) -> List[Dict[str, Any]]:
    """
    Fetch all mood analyses for a specific user

    Retrieves all mood analysis records associated with the given user,
    ordered by creation date in descending order (newest first).

    Args:
        db: Database session
        user_id: User identifier

    Returns:
        List of mood analysis records as dictionaries. Empty list if no records found.

    Raises:
        Exception: If database query fails
    """
    try:
        moods = db.query(MoodAnalysis).filter(
            MoodAnalysis.user_id == user_id
        ).order_by(MoodAnalysis.created_at.desc()).all()

        logger.info("Fetched %s mood records", len(moods))

        return [
            {
                "id": mood.id,
                "user_id": mood.user_id,
                "mood_analysed": mood.mood_analysed,
                "reason_for_mood": mood.reason_for_mood,
                "confidence_score": mood.confidence_score,
                "llm_provider": mood.llm_provider,
                "created_at": mood.created_at,
                "input_text": mood.input_text
            }
            for mood in moods
        ]

    except Exception:
        logger.exception("Failed to fetch mood records")
        raise


def get_user_feedback(
    db: Session,
    user_id: str
) -> List[Dict[str, Any]]:
    """
    Fetch all feedback submissions for a specific user

    Retrieves all feedback records associated with the given user,
    ordered by creation date in descending order (newest first).

    Args:
        db: Database session
        user_id: User identifier

    Returns:
        List of feedback records as dictionaries. Empty list if no records found.

    Raises:
        Exception: If database query fails
    """
    try:
        feedback_list = db.query(UserFeedback).filter(
            UserFeedback.user_id == user_id
        ).order_by(UserFeedback.created_at.desc()).all()

        logger.info("Fetched %s feedback records", len(feedback_list))

        return [
            {
                "id": feedback.id,
                "user_id": feedback.user_id,
                "feedback_text": feedback.feedback_text,
                "rating": feedback.rating,
                "created_at": feedback.created_at
            }
            for feedback in feedback_list
        ]

    except Exception:
        logger.exception("Failed to fetch feedback records")
        raise


def get_user_activities(
    db: Session,
    user_id: str
) -> List[Dict[str, Any]]:
    """
    Fetch all activity selections for a specific user

    Retrieves all activity selection records associated with the given user,
    ordered by creation date in descending order (newest first).

    Args:
        db: Database session
        user_id: User identifier

    Returns:
        List of activity selection records as dictionaries. Empty list if no records found.

    Raises:
        Exception: If database query fails
    """
    try:
        activities = db.query(UserActivitySelection).filter(
            UserActivitySelection.user_id == user_id
        ).order_by(UserActivitySelection.id.desc()).all()

        logger.info("Fetched %s activity records", len(activities))

        return [
            {
                "id": activity.id,
                "user_id": activity.user_id,
                "activity_id": activity.activity_id,
                "activity_name": activity.activity_name,
                "available_time_minutes": activity.available_time_minutes,
                "ai_session_title": activity.ai_session_title,
                "ai_estimated_duration": activity.ai_estimated_duration,
                "created_at": getattr(activity, 'created_at', datetime.utcnow())
            }
            for activity in activities
        ]

    except Exception:
        logger.exception("Failed to fetch activity records")
        raise


def get_user_moods_in_period(
    db: Session,
    user_id: str,
    from_date: datetime,
    to_date: datetime
) -> List[Dict[str, Any]]:
    """
    Fetch all mood analyses for a user within a specific date range

    Retrieves mood analysis records where the creation timestamp falls
    between from_date (inclusive) and to_date (inclusive).

    Args:
        db: Database session
        user_id: User identifier
        from_date: Start date of the period (inclusive)
        to_date: End date of the period (inclusive)

    Returns:
        List of mood analysis records within the date range as dictionaries.
        Empty list if no records found.

    Raises:
        ValueError: If from_date is after to_date
        Exception: If database query fails
    """
    try:
        if from_date > to_date:
            raise ValueError("from_date must be before or equal to to_date")

        moods = db.query(MoodAnalysis).filter(
            MoodAnalysis.user_id == user_id,
            MoodAnalysis.created_at >= from_date,
            MoodAnalysis.created_at <= to_date
        ).order_by(MoodAnalysis.created_at.asc()).all()

        logger.info(
            "Fetched %s mood records in requested period", len(moods)
        )

        return [
            {
                "id": mood.id,
                "user_id": mood.user_id,
                "mood_analysed": mood.mood_analysed,
                "reason_for_mood": mood.reason_for_mood,
                "confidence_score": mood.confidence_score,
                "llm_provider": mood.llm_provider,
                "created_at": mood.created_at,
                "input_text": mood.input_text
            }
            for mood in moods
        ]

    except ValueError as e:
        logger.warning(f"Invalid date range: {str(e)}")
        raise
    except Exception:
        logger.exception("Failed to fetch mood records in period")
        raise
