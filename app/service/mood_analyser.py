"""
Mood Analysis Service Layer
Handles LLM requests with fallback logic for ollama, groq, and gemini
"""
import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import httpx

from app.llm.config import LLMProvider, llm_config
from app.database import repository as db_repository

logger = logging.getLogger(__name__)

# Mood analysis prompt
MOOD_ANALYSIS_PROMPT = """Analyze the mood and emotional state from the following text. 
Respond ONLY with valid JSON (no markdown, no extra text) in this exact format:
{{
    "mood_analysed": "the detected mood (e.g., happy, sad, angry, anxious, neutral, etc.)",
    "reason_for_mood": "a brief explanation of why this mood was detected based on the text"
}}

Text to analyze: {text}"""


class MoodAnalyzerService:
    """
    Service for analyzing mood using LLM with fallback support
    Focuses on: LLM request, response validation, and processing
    Database operations delegated to database layer
    """

    def __init__(self, db: Session):
        self.db = db
        self.primary_provider = llm_config.get_primary_provider()
        self.fallback_provider = llm_config.get_fallback_provider()

    async def analyze_mood(self, user_id: str, text: str) -> Dict[str, Any]:
        """
        Analyze mood from text using LLM with fallback support
        
        Args:
            user_id: Unique user identifier
            text: Text to analyze
            
        Returns:
            Dictionary containing mood_analysed, reason_for_mood, and metadata
        """
        logger.info(f"Starting mood analysis for user: {user_id}")
        
        # Try primary provider first
        result = await self._try_llm_request(self.primary_provider, text)
        
        # If primary fails, try fallback
        if result is None:
            logger.warning(f"Primary provider ({self.primary_provider}) failed. Trying fallback ({self.fallback_provider})...")
            result = await self._try_llm_request(self.fallback_provider, text)
        
        # If both fail, return default/fallback response
        if result is None:
            logger.error("Both primary and fallback providers failed. Returning default response.")
            result = self._get_default_response()
            provider_used = "default"
        else:
            provider_used = result.get("provider_used", "unknown")
        
        # Validate result
        if not self._is_valid_response(result):
            logger.warning("Response validation failed. Using default response.")
            result = self._get_default_response()
            provider_used = "default"
        
        # Store mood analysis data in the mood_analysis table
        mood_record = db_repository.save_mood_analysis(
            db=self.db,
            user_id=user_id,
            input_text=text,
            mood_analysed=result.get("mood_analysed", "unknown"),
            reason_for_mood=result.get("reason_for_mood", "Unable to analyze"),
            confidence_score=result.get("confidence_score"),
            llm_provider=provider_used
        )

        return {
            "mood_analysed": result.get("mood_analysed"),
            "reason_for_mood": result.get("reason_for_mood"),
            "confidence_score": result.get("confidence_score"),
            "llm_provider": provider_used,
            "database_id": mood_record.id if mood_record else None
        }

    async def _try_llm_request(self, provider: LLMProvider, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt LLM request with specific provider
        
        Args:
            provider: LLM provider to use
            text: Text to analyze
            
        Returns:
            Dictionary with mood analysis or None if failed
        """
        try:
            if provider == LLMProvider.OLLAMA:
                return await self._call_ollama(text)
            elif provider == LLMProvider.GROQ:
                return await self._call_groq(text)
            elif provider == LLMProvider.GEMINI:
                return await self._call_gemini(text)
            else:
                logger.error(f"Unknown provider: {provider}")
                return None
        except Exception as e:
            logger.error(f"Error calling {provider}: {str(e)}")
            return None

    async def _call_ollama(self, text: str) -> Optional[Dict[str, Any]]:
        """Call Ollama API for mood analysis"""
        try:
            config = llm_config.ollama
            prompt = MOOD_ANALYSIS_PROMPT.format(text=text)
            
            async with httpx.AsyncClient(timeout=config.timeout) as client:
                response = await client.post(
                    f"{config.base_url}/api/generate",
                    json={
                        "model": config.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                    timeout=config.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "").strip()
                    
                    # Parse JSON response
                    parsed = self._parse_llm_response(response_text)
                    if parsed:
                        parsed["provider_used"] = LLMProvider.OLLAMA.value
                        parsed["confidence_score"] = 0.85  # Default confidence for ollama
                        return parsed
                
                logger.error(f"Ollama API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Ollama request failed: {str(e)}")
            return None

    async def _call_groq(self, text: str) -> Optional[Dict[str, Any]]:
        """Call Groq API for mood analysis"""
        try:
            config = llm_config.groq
            
            if not config.api_key:
                logger.error("Groq API key not configured")
                return None
            
            prompt = MOOD_ANALYSIS_PROMPT.format(text=text)
            
            async with httpx.AsyncClient(timeout=config.timeout) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {config.api_key}"},
                    json={
                        "model": config.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                    },
                    timeout=config.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    parsed = self._parse_llm_response(response_text)
                    if parsed:
                        parsed["provider_used"] = LLMProvider.GROQ.value
                        parsed["confidence_score"] = 0.90  # Default confidence for groq
                        return parsed
                
                logger.error(f"Groq API error: "f"{response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Groq request failed: {str(e)}")
            return None

    async def _call_gemini(self, text: str) -> Optional[Dict[str, Any]]:
        """Call Google Gemini API for mood analysis"""
        try:
            config = llm_config.gemini
            
            if not config.api_key:
                logger.error("Gemini API key not configured")
                return None
            
            prompt = MOOD_ANALYSIS_PROMPT.format(text=text)
            
            async with httpx.AsyncClient(timeout=config.timeout) as client:
                response = await client.post(
                    f"{config.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json"},
                    json={
                    "model": config.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                },
                    timeout=config.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    response_text = data["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    parsed = self._parse_llm_response(response_text)
                    if parsed:
                        parsed["provider_used"] = LLMProvider.GEMINI.value
                        parsed["confidence_score"] = 0.92  # Default confidence for gemini
                        return parsed
                
                logger.error(f"Gemini API error: "f"{response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Gemini request failed: {str(e)}")
            return None

    def _parse_llm_response(self,response_text: str) -> Optional[Dict[str, str]]:
        """Parse and validate LLM JSON response """
        try:

            logger.info(f"Raw LLM Response: {response_text}")

            response_text = response_text.strip()

            # Remove markdown code fences
            response_text = response_text.replace(
                "```json",
                ""
            )

            response_text = response_text.replace(
                "```",
                ""
            )

            response_text = response_text.strip()

            # Parse JSON
            parsed = json.loads(response_text)

            # Validate required fields
            mood = parsed.get("mood_analysed")
            reason = parsed.get("reason_for_mood")

            if not mood or not reason:
                logger.warning(
                    f"Missing required fields in response: {parsed}"
                )
                return None

            return {
                "mood_analysed": str(mood).strip(),
                "reason_for_mood": str(reason).strip(),
            }

        except json.JSONDecodeError as e:

            logger.error(
                f"JSON parsing failed: {str(e)}"
            )

            logger.error(
                f"Invalid JSON response received: {response_text}"
            )

            return None

        except Exception as e:

            logger.error(
                f"Unexpected parsing error: {str(e)}"
            )

            return None
        

    def _get_default_response(self) -> Dict[str, Any]:
        """
        Return default response when all LLM providers fail
        
        Returns:
            Default mood analysis response
        """
        return {
            "mood_analysed": "neutral",
            "reason_for_mood": "Unable to analyze mood due to service unavailability. Please try again later.",
            "confidence_score": 0.0,
            "provider_used": "default"
        }

    def _is_valid_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate LLM response has required fields
        
        Args:
            response: Response dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["mood_analysed", "reason_for_mood"]
        return all(field in response and response[field] for field in required_fields)
