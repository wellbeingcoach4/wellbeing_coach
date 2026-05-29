"""
Feedback Service Module.

Handles user feedback operations for the Wellbeing Coach
application, including saving and retrieving feedback
data through the database repository layer.
"""


import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.database import repository

logger = logging.getLogger(__name__)


class FeedbackService:

    def __init__(self, db: Session):
        self.db = db

    def save_feedback(
        self,
        user_id: str,
        feedback_text: str,
        activity_selection: str,
        user_activity_selection_id: int,
        rating: Optional[int] = None,
    ):
        selection = repository.get_user_activity_selection_by_id(
            self.db, user_activity_selection_id
        )
        if not selection or selection.user_id != user_id:
            raise ValueError("Invalid user_activity_selection_id for user")

        logger.info(
            "Saving user feedback rating_provided=%s user_activity_selection_id=%s",
            rating is not None,
            user_activity_selection_id,
        )
        saved = repository.save_feedback(
            db=self.db,
            user_id=user_id,
            feedback_text=feedback_text,
            rating=rating,
            activity_selection=activity_selection.strip(),
            user_activity_selection_id=user_activity_selection_id,
        )

        if not saved:
            logger.warning("Feedback save failed in repository layer")
            raise ValueError("Failed to save feedback")

        logger.info("Feedback saved successfully")
        return {
            "message": "Feedback saved successfully",
            "database_id": saved.id,
            "thanks_note": "Thanks for your feedback!"
        }
