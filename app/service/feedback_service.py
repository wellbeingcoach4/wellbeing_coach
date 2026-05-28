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
        rating: Optional[int] = None,
        activity_selection_id: Optional[int] = None,
    ):
        logger.info(
            "Saving user feedback rating_provided=%s activity_linked=%s",
            rating is not None,
            activity_selection_id is not None,
        )
        saved = repository.save_feedback(
            db=self.db,
            user_id=user_id,
            feedback_text=feedback_text,
            rating=rating,
            activity_selection_id=activity_selection_id,
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
