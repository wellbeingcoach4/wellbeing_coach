from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schema.wellbeing_schema import (
    WellbeingActivitiesListResponse,
    ActivitySelectionRequest,
    ActivitySelectionResponse
)

from app.service.wellbeing_service import WellbeingService

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

    try:

        service = WellbeingService(db)

        return await service.select_activity(
            user_id=request.user_id,
            activity_id=request.activity_id,
            available_time_minutes=request.available_time_minutes,
            mood=request.mood
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )