"""
Feedback Routes Module.

Defines API endpoints for handling user feedback
operations in the Wellbeing Coach application.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schema.feedback_schema import FeedbackRequest, FeedbackResponse
from app.service.feedback_service import FeedbackService

router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"]
)


@router.post("/", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    try:
        service = FeedbackService(db)
        return service.save_feedback(
            user_id=request.user_id,
            feedback_text=request.feedback_text,
            rating=request.rating
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
