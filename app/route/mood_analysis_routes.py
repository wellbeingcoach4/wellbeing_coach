"""
Routes for mood analysis endpoints
"""
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schema.mood_schema import MoodRequest, MoodResponse
from app.database import get_db
from app.service.mood_analyser import MoodAnalyzerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mood", tags=["mood"])


@router.post("/analyze_mood", response_model=MoodResponse)
async def analyze_mood(
    request: MoodRequest,
    db: Session = Depends(get_db)
) -> MoodResponse:
    """
    Analyze mood from input text

    Workflow:
    1. Service processes text and calls LLM
    2. Service validates response
    3. Service calls database layer to store
    4. Returns result with database ID

    Args:
        request: MoodRequest containing user_id and text
        db: Database session

    Returns:
        MoodResponse with mood analysis results
    """
    logger.info("Analyzing mood request received")
    try:
        service = MoodAnalyzerService(db=db)
        result = await service.analyze_mood(
            user_id=request.user_id,
            text=request.text
        )

        return MoodResponse(**result)
    except Exception:
        logger.exception("Unhandled exception during mood analysis")
        raise
