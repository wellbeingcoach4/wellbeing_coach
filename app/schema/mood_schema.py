"""
Mood Schema Module.

Defines request and response validation schemas
for mood analysis operations in the Wellbeing
Coach application.
"""
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class MoodRequest(BaseModel):
    user_id: str = Field(..., min_length=1,max_length=6, pattern=r"^[a-zA-Z0-9_-]+$",
    description="Unique identifier for the user")
    text: str = Field(..., min_length=1,max_length=1000, description="The text to analyze for mood")

class MoodResponse(BaseModel):
    mood_analysed: str = Field(..., description="The detected mood")
    reason_for_mood: str = Field(...,
                                 description="Reason/explanation for the detected mood")
    confidence_score: float = Field(
        default=0.85, ge=0, le=1, description="The confidence level of the mood detection")
    llm_provider: str = Field(
        default="ollama", description="The LLM provider used for analysis")
    database_id: Optional[int] = Field(
        default=None, description="Database record ID")
