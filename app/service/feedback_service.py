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

    def save_feedback(self, user_id: str, feedback_text: str, rating: Optional[int] = None):
        saved = repository.save_feedback(
            db=self.db,
            user_id=user_id,
            feedback_text=feedback_text,
            rating=rating
        )

        if not saved:
            raise ValueError("Failed to save feedback")

        return {
            "message": "Feedback saved successfully",
            "database_id": saved.id,
            "thanks_note": "Thanks for your feedback!"
        }
