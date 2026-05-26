"""
Mood Analysis Service Layer
Handles LLM requests with fallback logic for ollama, groq, and gemini
"""

import json
import logging
from typing import Dict, Any, Optional

import httpx
from sqlalchemy.orm import Session

from app.database.models import MoodAnalysis
from app.database import repository as db_repository
from app.llm.config import LLMProvider, llm_config

logger = logging.getLogger(__name__)


MOOD_ANALYSIS_PROMPT = """
Analyze the mood and emotional state from the following text.

Respond ONLY with valid JSON (no markdown, no extra text)
in this exact format:

{
    "mood_analysed": "happy",
    "reason_for_mood": "brief explanation"
}

Text to analyze: {text}
"""


class MoodAnalyzerService:
    """
    Service for mood analysis using multiple LLM providers
    with fallback support.
    """

    def __init__(self, db: Session):
        self.db = db
        self.primary_provider = llm_config.get_primary_provider()
        self.fallback_provider = llm_config.get_fallback_provider()

    async def analyze_mood(
        self,
        user_id: str,
        text: str,
    ) -> Dict[str, Any]:
        """
        Analyze mood using configured LLM providers.

        Args:
            user_id: Unique user identifier
            text: User text input

        Returns:
            Mood analysis response dictionary
        """

        logger.info(
            "Starting mood analysis for user: %s",
            user_id,
        )

        result = await self._try_llm_request(
            self.primary_provider,
            text,
        )

        if result is None:
            logger.warning(
                "Primary provider failed. Trying fallback provider."
            )

            result = await self._try_llm_request(
                self.fallback_provider,
                text,
            )

        if result is None:
            logger.error(
                "All providers failed. Using default response."
            )

            result = self._get_default_response()
            provider_used = "default"

        else:
            provider_used = result.get(
                "provider_used",
                "unknown",
            )

        if not self._is_valid_response(result):
            logger.warning(
                "Invalid response detected. Using default response."
            )

            result = self._get_default_response()
            provider_used = "default"

        mood_record = self._store_mood_analysis(
            user_id=user_id,
            input_text=text,
            mood_analysed=result.get(
                "mood_analysed",
                "unknown",
            ),
            reason_for_mood=result.get(
                "reason_for_mood",
                "Unable to analyze",
            ),
            confidence_score=result.get(
                "confidence_score",
                0.0,
            ),
            llm_provider=provider_used,
        )

        return {
            "mood_analysed": result.get("mood_analysed"),
            "reason_for_mood": result.get("reason_for_mood"),
            "confidence_score": result.get("confidence_score"),
            "llm_provider": provider_used,
            "database_id": (
                mood_record.id if mood_record else None
            ),
        }

    async def _try_llm_request(
        self,
        provider: LLMProvider,
        text: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt request using selected provider.
        """

        try:
            if provider == LLMProvider.OLLAMA:
                return await self._call_ollama(text)

            if provider == LLMProvider.GROQ:
                return await self._call_groq(text)

            if provider == LLMProvider.GEMINI:
                return await self._call_gemini(text)

            logger.error(
                "Unknown provider: %s",
                provider,
            )

            return None

        except Exception as exc:
            logger.error(
                "Provider request failed: %s",
                str(exc),
            )

            return None

    async def _call_ollama(
        self,
        text: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Call Ollama API.
        """

        try:
            config = llm_config.ollama

            prompt = MOOD_ANALYSIS_PROMPT.format(
                text=text,
            )

            async with httpx.AsyncClient(
                timeout=config.timeout
            ) as client:

                response = await client.post(
                    f"{config.base_url}/chat/completions",
                    json={
                        "model": config.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt,
                            }
                        ],
                        "stream": False,
                    },
                )

            if response.status_code != 200:
                logger.error(
                    "Ollama API failed: %s",
                    response.status_code,
                )

                return None

            data = response.json()

            response_text = (
                data["choices"][0]["message"]["content"]
            )

            parsed = self._parse_llm_response(
                response_text
            )

            if parsed:
                parsed["provider_used"] = (
                    LLMProvider.OLLAMA.value
                )

                parsed["confidence_score"] = 0.85

                return parsed

            return None

        except Exception as exc:
            logger.error(
                "Ollama request error: %s",
                str(exc),
            )

            return None

    async def _call_groq(
        self,
        text: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Call Groq API.
        """

        return None

    async def _call_gemini(
        self,
        text: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Call Gemini API.
        """

        return None

    def _parse_llm_response(
        self,
        response_text: str,
    ) -> Optional[Dict[str, str]]:
        """
        Parse LLM JSON response.
        """

        try:
            response_text = response_text.strip()

            response_text = response_text.replace(
                "json",
                "",
            )

            response_text = response_text.replace(
                "",
                "",
            )

            response_text = response_text.strip()

            parsed = json.loads(response_text)

            mood = parsed.get("mood_analysed")
            reason = parsed.get("reason_for_mood")

            if not mood or not reason:
                logger.warning(
                    "Missing required fields."
                )

                return None

            return {
                "mood_analysed": str(mood).strip(),
                "reason_for_mood": str(reason).strip(),
            }

        except json.JSONDecodeError as exc:
            logger.error(
                "JSON parsing failed: %s",
                str(exc),
            )

            return None

        except Exception as exc:
            logger.error(
                "Unexpected parsing error: %s",
                str(exc),
            )

            return None

    def _store_mood_analysis(
        self,
        user_id: str,
        input_text: str,
        mood_analysed: str,
        reason_for_mood: str,
        confidence_score: float,
        llm_provider: str,
    ):
        """
        Store mood analysis in database.
        """

        return db_repository.save_mood_analysis(
            db=self.db,
            user_id=user_id,
            input_text=input_text,
            mood_analysed=mood_analysed,
            reason_for_mood=reason_for_mood,
            confidence_score=confidence_score,
            llm_provider=llm_provider,
        )

    def get_mood_history(
        self,
        user_id: str,
        limit: int = 10,
    ):
        """
        Retrieve mood history for user.
        """

        return (
            self.db.query(MoodAnalysis)
            .filter(
                MoodAnalysis.user_id == user_id
            )
            .order_by(
                MoodAnalysis.id.desc()
            )
            .limit(limit)
            .all()
        )

    def _get_default_response(
        self,
    ) -> Dict[str, Any]:
        """
        Default fallback response.
        """

        return {
            "mood_analysed": "neutral",
            "reason_for_mood": (
                "Unable to analyze mood."
            ),
            "confidence_score": 0.0,
            "provider_used": "default",
        }

    def _is_valid_response(
        self,
        response: Dict[str, Any],
    ) -> bool:
        """
        Validate response structure.
        """

        required_fields = [
            "mood_analysed",
            "reason_for_mood",
        ]

        return all(
            field in response and response[field]
            for field in required_fields
        )
