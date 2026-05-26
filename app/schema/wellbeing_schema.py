"""
Wellbeing Schema Module.

Defines request and response schemas for wellbeing
activities, activity selection, and personalized
wellbeing session operations in the Wellbeing
Coach application.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class WellbeingActivityResponse(BaseModel):

    activity_id: int

    activity_name: str

    description: str


class WellbeingActivitiesListResponse(BaseModel):

    activities: List[WellbeingActivityResponse]


class ActivitySelectionRequest(BaseModel):

    user_id: str = Field(..., min_length=1,
                         pattern=r"^[a-zA-Z0-9_-]+$", description="Unique identifier for the user")

    activity_id: int

    available_time_minutes: Optional[int] = Field(
        None, description="Available time in minutes for the activity")

    mood: Optional[str] = None

    user_reason_for_mood: Optional[str] = Field(
        None, max_length=500, description="User's reason for their current mood")

    custom_activity: Optional[str] = Field(
        None, min_length=3, max_length=255, description="Custom activity provided by user if not selecting from suggestions")

    @model_validator(mode="after")
    def validate_custom_activity_with_zero_id(self):

        if self.activity_id == 0 and not self.custom_activity:
            raise ValueError(
                "activity_id 0 requires custom_activity"
            )

        return self


class SessionPlanResponse(BaseModel):

    session_title: str

    session_steps: List[str]

    estimated_duration: str

    provider_used: str

    mood_addressed: Optional[str] = None


class ActivitySelectionResponse(BaseModel):

    message: str

    activity_name: str

    available_time_minutes: Optional[int]

    session_plan: (SessionPlanResponse)

    database_id: int
