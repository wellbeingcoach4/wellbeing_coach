from pydantic import BaseModel, Field
from typing import Optional


class FeedbackRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    feedback_text: str = Field(..., min_length=1)
    rating: Optional[int] = Field(None, ge=1, le=5)


class FeedbackResponse(BaseModel):
    message: str
    database_id: int
    thanks_note: str
