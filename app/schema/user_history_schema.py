"""
Schema definitions for user history APIs
Contains Pydantic models for user history and periodic mood analysis
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class MoodHistoryItem(BaseModel):
    """
    Individual mood analysis history item
    """
    id: int = Field(..., description="Database record ID")
    user_id: str = Field(..., description="User identifier")
    mood_analysed: str = Field(..., description="The detected mood")
    reason_for_mood: str = Field(..., description="Reason/explanation for the detected mood")
    confidence_score: float = Field(default=0.85, ge=0, le=1, description="Confidence level of mood detection")
    llm_provider: str = Field(..., description="LLM provider used for analysis")
    created_at: datetime = Field(..., description="Timestamp when mood was analyzed")
    input_text: Optional[str] = Field(None, description="Original input text for the mood analysis")


class FeedbackHistoryItem(BaseModel):
    """
    Individual feedback history item
    """
    id: int = Field(..., description="Database record ID")
    user_id: str = Field(..., description="User identifier")
    feedback_text: str = Field(..., description="Feedback text provided by user")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating given by user (1-5)")
    created_at: datetime = Field(..., description="Timestamp when feedback was submitted")


class ActivityHistoryItem(BaseModel):
    """
    Individual activity selection history item
    """
    id: int = Field(..., description="Database record ID")
    user_id: str = Field(..., description="User identifier")
    activity_id: int = Field(..., description="Activity identifier")
    activity_name: str = Field(..., description="Name of the selected activity")
    available_time_minutes: Optional[int] = Field(None, description="Available time for the activity")
    ai_session_title: str = Field(..., description="AI generated session title")
    ai_estimated_duration: str = Field(..., description="AI estimated duration for the activity")
    created_at: datetime = Field(default=datetime.utcnow, description="Timestamp when activity was selected")


class UserHistoryResponse(BaseModel):
    """
    Complete user history response containing moods, feedback, and activities
    """
    user_id: str = Field(..., description="User identifier")
    mood_history: List[MoodHistoryItem] = Field(default=[], description="List of mood analyses")
    feedback_history: List[FeedbackHistoryItem] = Field(default=[], description="List of feedback submissions")
    activity_history: List[ActivityHistoryItem] = Field(default=[], description="List of activity selections")
    total_moods: int = Field(default=0, description="Total number of mood analyses")
    total_feedback: int = Field(default=0, description="Total number of feedback submissions")
    total_activities: int = Field(default=0, description="Total number of activities selected")


class PeriodicMoodItem(BaseModel):
    """
    Mood item for periodic analysis
    """
    id: int = Field(..., description="Database record ID")
    mood_analysed: str = Field(..., description="The detected mood")
    reason_for_mood: str = Field(..., description="Reason for the mood")
    confidence_score: float = Field(..., description="Confidence score of mood detection")
    llm_provider: str = Field(..., description="LLM provider used for analysis")
    created_at: datetime = Field(..., description="Timestamp of mood analysis")


class MoodStatistics(BaseModel):
    """
    Statistical summary of moods for a period
    """
    total_moods: int = Field(..., description="Total number of moods in the period")
    mood_distribution: dict = Field(..., description="Distribution of each mood type with count")
    average_confidence: float = Field(..., description="Average confidence score across all moods")
    most_common_mood: Optional[str] = Field(None, description="Most frequently detected mood in the period")
    least_common_mood: Optional[str] = Field(None, description="Least frequently detected mood in the period")


class PeriodicMoodResponse(BaseModel):
    """
    Response containing mood analysis for a specific date range
    """
    user_id: str = Field(..., description="User identifier")
    from_date: datetime = Field(..., description="Start date of the period (inclusive)")
    to_date: datetime = Field(..., description="End date of the period (inclusive)")
    llm_provider: str = Field(..., description="LLM provider used for analysis")
    moods_in_period: List[PeriodicMoodItem] = Field(default=[], description="List of moods in the specified period")
    mood_statistics: MoodStatistics = Field(..., description="Statistical summary of moods")
    period_analysis: str = Field(..., description="Overall analysis of user's mood during the period")
    recommendation: str = Field(..., description="AI-generated recommendation based on the mood analysis")
