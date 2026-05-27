"""
Wellbeing Coach - AI-powered mood analysis and wellbeing support system
"""
from app.core.logger import setup_logging
from app.database import MoodAnalysis, get_db, init_db, close_db
from app.service import MoodAnalyzerService
from app.llm import llm_config, LLMProvider

setup_logging()

__version__ = "0.1.0"
__all__ = [
    "MoodAnalysis",
    "get_db",
    "init_db",
    "close_db",
    "MoodAnalyzerService",
    "llm_config",
    "LLMProvider",
]
