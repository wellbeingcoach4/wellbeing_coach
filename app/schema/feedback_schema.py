from typing import Optional
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    feedback_text: str = Field(..., min_length=1)
    rating: Optional[int] = Field(None, ge=1, le=5)
    activity_selection_id: Optional[int] = Field(
        None,
        description="ID of the activity session this feedback refers to",
    )


class FeedbackResponse(BaseModel):
    message: str
    database_id: int
    thanks_note: str
