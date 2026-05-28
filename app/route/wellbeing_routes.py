import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schema.wellbeing_schema import (
    WellbeingActivitiesListResponse,
    ActivitySelectionRequest,
    ActivitySelectionResponse
)

from app.service.wellbeing_service import WellbeingService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/wellbeing",
    tags=["Wellbeing"]
)

@router.get(
    "/activities",
    response_model=WellbeingActivitiesListResponse
)
def get_activities(
    db: Session = Depends(get_db)
):
    logger.info("Fetching wellbeing activities catalog")

    service = WellbeingService(db)

    return service.get_available_activities()


@router.post(
    "/select-activity",
    response_model=ActivitySelectionResponse
)
async def select_activity(
    request: ActivitySelectionRequest,
    db: Session = Depends(get_db)
):
    logger.info(
        "Selecting wellbeing activity activity_id=%s custom_activity_provided=%s",
        request.activity_id,
        bool(getattr(request, "custom_activity", None)),
    )

    try:

        service = WellbeingService(db)

        return await service.select_activity(
            user_id=request.user_id,
            activity_id=request.activity_id,
            available_time_minutes=request.available_time_minutes,
            mood=request.mood,
            user_reason_for_mood=getattr(request, 'user_reason_for_mood', None),
            custom_activity=getattr(request, 'custom_activity', None)
        )

    except ValueError as e:
        logger.warning("Activity selection validation failed: %s", str(e))
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception:
        logger.exception("Unhandled exception in wellbeing activity selection")
        raise
