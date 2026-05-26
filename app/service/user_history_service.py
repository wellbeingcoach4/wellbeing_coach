"""
User History Service Layer
Handles user history retrieval and periodic mood analysis
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import httpx

from app.database import repository as db_repository
from app.llm.config import llm_config, LLMProvider

logger = logging.getLogger(__name__)


PERIODIC_MOOD_ANALYSIS_PROMPT = """Analyze the following mood history data for a user over a specific period.
Provide insights about their emotional wellbeing and give recommendations.

Mood Data:
{mood_data}

Instructions:
- Analyze the overall emotional trend
- Identify patterns or recurring moods
- Provide a concise summary of the user's emotional state during this period
- Give actionable recommendations for wellbeing
- Return ONLY valid JSON (no markdown, no extra text)

Return response in this format:
{{
    "period_analysis": "A 2-3 sentence analysis of the user's mood during this period",
    "recommendation": "A specific, actionable recommendation based on the mood analysis"
}}
"""


class UserHistoryService:
    """
    Service for fetching and analyzing user history data
    Focuses on: Data retrieval, aggregation, and LLM-based analysis
    Database operations delegated to repository layer
    """

    def __init__(self, db: Session):
        """
        Initialize UserHistoryService
        
        Args:
            db: Database session for performing queries
        """
        self.db = db
        self.primary_provider = llm_config.get_primary_provider()
        self.fallback_provider = llm_config.get_fallback_provider()

    def get_user_history(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch complete user history including moods, feedback, and activities
        
        This method retrieves all historical data for a specific user from the database,
        aggregating mood analyses, feedback submissions, and activity selections.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            Dictionary containing:
                - mood_history: List of MoodAnalysis records
                - feedback_history: List of UserFeedback records
                - activity_history: List of UserActivitySelection records
                - total_moods: Count of mood analyses
                - total_feedback: Count of feedback submissions
                - total_activities: Count of activity selections
                
        Raises:
            ValueError: If user_id is invalid
            Exception: If database query fails
        """
        try:
            logger.info(f"Fetching history for user: {user_id}")
            
            # Fetch all moods for the user
            mood_history = db_repository.get_user_moods(self.db, user_id)
            
            # Fetch all feedback for the user
            feedback_history = db_repository.get_user_feedback(self.db, user_id)
            
            # Fetch all activities for the user
            activity_history = db_repository.get_user_activities(self.db, user_id)
            
            logger.info(
                f"Successfully fetched history for user {user_id}: "
                f"{len(mood_history)} moods, {len(feedback_history)} feedback, "
                f"{len(activity_history)} activities"
            )
            
            return {
                "user_id": user_id,
                "mood_history": mood_history,
                "feedback_history": feedback_history,
                "activity_history": activity_history,
                "total_moods": len(mood_history),
                "total_feedback": len(feedback_history),
                "total_activities": len(activity_history)
            }
            
        except Exception as e:
            logger.error(f"Error fetching history for user {user_id}: {str(e)}")
            raise

    async def get_periodic_mood(
        self,
        user_id: str,
        from_date: datetime,
        to_date: datetime
    ) -> Dict[str, Any]:
        """
        Fetch and analyze user's mood for a specific date range
        
        This method retrieves all mood analyses within a given period, calculates
        mood statistics, and generates AI-based analysis and recommendations.
        
        Args:
            user_id: Unique user identifier
            from_date: Start date of the analysis period (inclusive)
            to_date: End date of the analysis period (inclusive)
            
        Returns:
            Dictionary containing:
                - user_id: User identifier
                - from_date: Start date
                - to_date: End date
                - moods_in_period: List of mood records
                - mood_statistics: Statistics dict with mood distribution
                - period_analysis: AI-generated analysis of the period
                - recommendation: AI-generated recommendation
                
        Raises:
            ValueError: If date range is invalid (from_date > to_date)
            Exception: If database query or LLM analysis fails
        """
        try:
            # Validate date range
            if from_date > to_date:
                raise ValueError("from_date must be before or equal to to_date")
            
            logger.info(
                f"Fetching periodic mood for user {user_id} from {from_date} to {to_date}"
            )
            
            # Fetch moods within the date range
            moods_in_period = db_repository.get_user_moods_in_period(
                self.db, user_id, from_date, to_date
            )
            
            # Calculate mood statistics
            mood_statistics = self._calculate_mood_statistics(moods_in_period)
            
            # Generate AI-based analysis and recommendation
            ai_analysis = await self._generate_mood_analysis(
                user_id=user_id,
                mood_data=moods_in_period,
                from_date=from_date,
                to_date=to_date
            )
            
            result = {
                "user_id": user_id,
                "from_date": from_date,
                "to_date": to_date,
                "moods_in_period": moods_in_period,
                "mood_statistics": mood_statistics,
                "period_analysis": ai_analysis.get("period_analysis", ""),
                "recommendation": ai_analysis.get("recommendation", "")
            }
            
            logger.info(
                f"Successfully fetched periodic mood for user {user_id}: "
                f"{len(moods_in_period)} moods found in period"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Error fetching periodic mood for user {user_id} ({from_date} to {to_date}): {str(e)}"
            )
            raise

    def _calculate_mood_statistics(self, moods: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistical summary of moods
        
        Computes mood distribution, average confidence scores, and identifies
        the most and least common moods.
        
        Args:
            moods: List of mood analysis records
            
        Returns:
            Dictionary containing:
                - total_moods: Total count
                - mood_distribution: Dict with mood types and their counts
                - average_confidence: Mean confidence score
                - most_common_mood: Most frequent mood
                - least_common_mood: Least frequent mood
        """
        if not moods:
            return {
                "total_moods": 0,
                "mood_distribution": {},
                "average_confidence": 0.0,
                "most_common_mood": None,
                "least_common_mood": None
            }
        
        # Count mood distribution
        mood_distribution = {}
        total_confidence = 0
        
        for mood in moods:
            mood_name = mood.get("mood_analysed", "unknown")
            mood_distribution[mood_name] = mood_distribution.get(mood_name, 0) + 1
            total_confidence += mood.get("confidence_score", 0)
        
        # Calculate averages and find extremes
        average_confidence = total_confidence / len(moods) if moods else 0
        most_common_mood = max(mood_distribution, key=mood_distribution.get) if mood_distribution else None
        least_common_mood = min(mood_distribution, key=mood_distribution.get) if mood_distribution else None
        
        return {
            "total_moods": len(moods),
            "mood_distribution": mood_distribution,
            "average_confidence": round(average_confidence, 3),
            "most_common_mood": most_common_mood,
            "least_common_mood": least_common_mood
        }

    async def _generate_mood_analysis(
        self,
        user_id: str,
        mood_data: List[Dict[str, Any]],
        from_date: datetime,
        to_date: datetime
    ) -> Dict[str, str]:
        """
        Generate AI-based analysis and recommendations for mood data
        
        Uses LLM to analyze mood patterns and provide personalized recommendations.
        Implements fallback logic for multiple LLM providers.
        
        Args:
            user_id: User identifier for logging
            mood_data: List of mood records to analyze
            from_date: Period start date
            to_date: Period end date
            
        Returns:
            Dictionary containing:
                - period_analysis: Analysis of mood during the period
                - recommendation: Recommendation for wellbeing
        """
        # Format mood data for LLM
        formatted_mood_data = self._format_mood_data_for_llm(mood_data)
        
        prompt = PERIODIC_MOOD_ANALYSIS_PROMPT.format(mood_data=formatted_mood_data)
        
        # Try with primary provider
        try:
            response = await self._call_llm(self.primary_provider, prompt)
            return self._parse_llm_response(response)
        except Exception as e:
            logger.warning(
                f"Primary LLM provider failed for user {user_id}: {str(e)}. "
                f"Attempting fallback provider."
            )
            
            # Try with fallback provider
            try:
                response = await self._call_llm(self.fallback_provider, prompt)
                return self._parse_llm_response(response)
            except Exception as fallback_error:
                logger.error(
                    f"All LLM providers failed for user {user_id}: {str(fallback_error)}"
                )
                # Return default response if all providers fail
                return {
                    "period_analysis": "Unable to generate analysis at this time.",
                    "recommendation": "Please try again later."
                }

    def _format_mood_data_for_llm(self, mood_data: List[Dict[str, Any]]) -> str:
        """
        Format mood data into a readable string for LLM analysis
        
        Args:
            mood_data: List of mood records
            
        Returns:
            Formatted string suitable for LLM input
        """
        if not mood_data:
            return "No mood data available for the period."
        
        formatted = []
        for mood in mood_data:
            formatted.append(
                f"- {mood.get('created_at', 'Unknown date')}: {mood.get('mood_analysed', 'Unknown')} "
                f"(confidence: {mood.get('confidence_score', 0):.2f})"
            )
        
        return "\n".join(formatted)

    async def _call_llm(self, provider: Optional[LLMProvider], prompt: str) -> str:
        """
        Call LLM with the specified provider
        
        Args:
            provider: LLM provider configuration
            prompt: Prompt to send to the LLM
            
        Returns:
            LLM response string
            
        Raises:
            Exception: If LLM call fails
        """
        if not provider:
            raise ValueError("No LLM provider available")

        # Use provider-specific configuration from llm_config
        config = llm_config.get_config_for_provider(provider)

        try:
            async with httpx.AsyncClient(timeout=config.timeout) as client:
                if provider == LLMProvider.OLLAMA:
                    url = f"{config.base_url}/api/generate"
                    payload = {
                        "model": config.model,
                        "prompt": prompt,
                        "stream": False
                    }
                    response = await client.post(url, json=payload)
                elif provider == LLMProvider.GROQ:
                    if not config.api_key:
                        raise ValueError("Groq API key not configured")
                    url = f"{config.base_url}/chat/completions"
                    response = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {config.api_key}"},
                        json={
                            "model": config.model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.3,
                            "stream": False
                        }
                    )
                elif provider == LLMProvider.GEMINI:
                    if not config.api_key:
                        raise ValueError("Gemini API key not configured")
                    url = f"{config.base_url}/models/{config.model}:generateContent"
                    response = await client.post(
                        url,
                        params={"key": config.api_key},
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": 0.3}
                        }
                    )
                else:
                    raise ValueError(f"Unknown LLM provider: {provider}")

                response.raise_for_status()
                result = response.json()

                if provider == LLMProvider.OLLAMA:
                    return result.get("response", "")
                if provider == LLMProvider.GROQ:
                    return result["choices"][0]["message"]["content"]
                if provider == LLMProvider.GEMINI:
                    return result["candidates"][0]["content"]["parts"][0]["text"]

                return result.get("content", "")

        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise

    def _parse_llm_response(self, response: str) -> Dict[str, str]:
        """
        Parse and validate LLM response
        
        Args:
            response: Raw LLM response
            
        Returns:
            Dictionary with period_analysis and recommendation
        """
        import json
        
        try:
            # Try to extract JSON from response
            parsed = json.loads(response)
            
            return {
                "period_analysis": parsed.get("period_analysis", ""),
                "recommendation": parsed.get("recommendation", "")
            }
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
            return {
                "period_analysis": response,
                "recommendation": "Please review the analysis above."
            }
