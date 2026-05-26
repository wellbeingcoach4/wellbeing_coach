"""
Database models for mood analysis
"""
from datetime import datetime
from sqlalchemy import JSON, Column, String, Float, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class MoodAnalysis(Base):
    """
    Model to store mood analysis results in PostgreSQL
    """
    __tablename__ = "mood_analysis"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True, nullable=False)
    input_text = Column(Text, nullable=False)
    mood_analysed = Column(String(100), nullable=False)
    reason_for_mood = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=True)
    llm_provider = Column(String(50), nullable=False)  # ollama, groq, or gemini
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MoodAnalysis(user_id={self.user_id}, mood={self.mood_analysed}, llm_provider={self.llm_provider})>"


class UserActivitySelection(Base):

    __tablename__ = "user_activity_selection"

    id = Column(Integer, primary_key=True)

    user_id = Column(String, nullable=False)

    activity_id = Column(Integer, nullable=False)

    activity_name = Column(String, nullable=False)

    available_time_minutes = Column(Integer)

    ai_session_title = Column(Text)

    ai_session_steps = Column(JSON)

    ai_estimated_duration = Column(String)

    llm_provider = Column(String)
    
    user_reason_for_mood = Column(Text, nullable=True)

    custom_activity = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserFeedback(Base):
    """
    Model to store user feedback for sessions
    """
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True, nullable=False)
    feedback_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)