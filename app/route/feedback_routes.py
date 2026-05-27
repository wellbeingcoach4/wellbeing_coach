import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schema.feedback_schema import FeedbackRequest, FeedbackResponse
from app.service.feedback_service import FeedbackService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"]
)


@router.post("/", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    logger.info("Submitting feedback rating_provided=%s", request.rating is not None)
    try:
        service = FeedbackService(db)
        return service.save_feedback(
            user_id=request.user_id,
            feedback_text=request.feedback_text,
            rating=request.rating
        )
    except ValueError as e:
        logger.warning("Feedback submission validation failed: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unhandled exception while submitting feedback")
        raise HTTPException(status_code=500, detail=str(e))
