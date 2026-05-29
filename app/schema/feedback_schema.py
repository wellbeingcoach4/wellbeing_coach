from typing import Optional
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    feedback_text: str = Field(..., min_length=1)
    rating: Optional[int] = Field(None, ge=1, le=5)
    activity_selection: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Activity name for the session being reviewed",
    )
    user_activity_selection_id: int = Field(
        ...,
        description="ID of the user_activity_selection session this feedback refers to",
    )


class FeedbackResponse(BaseModel):
    message: str
    database_id: int
    thanks_note: str
