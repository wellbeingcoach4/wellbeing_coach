"""
Wellbeing Service Module.

This module handles personalized wellbeing session
generation for the Wellbeing Coach application using
AI-powered recommendations, emotional analysis,
wellness activities, and session planning.
"""


import json
import logging
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.database.wellbeing_queries import WELLBEING_ACTIVITIES
from app.database import repository

from app.llm.config import llm_config, LLMProvider

logger = logging.getLogger(__name__)


WELLBEING_SESSION_PROMPT = """
You are an AI wellbeing coach specializing in personalized mental health support.

Generate a personalized wellbeing session for the user based on their current emotional state, activity preference, and their past feedback on previous sessions.

User's Current Mood:
{mood}

User's Reason For Mood:
{user_reason}

Custom Activity Provided (if any):
{custom_activity}

Activity Selected:
{activity_name}

User Available Time:
{available_time}

User's Past Feedback On Previous Sessions (most recent first; use this to refine recommendations):
{past_feedback}

Instructions:
- Tailor the session steps specifically to address the user's current mood
- If mood is anxious: include calming, grounding techniques
- If mood is sad: include uplifting, motivational elements
- If mood is stressed: include stress-relief techniques
- If a custom activity is provided, use it as the selected activity and center the session around that custom choice
- Personalize based on past feedback:
    * Lean into styles/techniques the user rated 4 or 5 stars
    * Avoid or reframe techniques the user rated 1 or 2 stars or complained about in feedback_text
    * If past feedback is "No prior feedback", rely on mood and activity alone
- Keep the response practical and actionable
- Keep it concise and appropriate for their emotional state
- Adjust suggestions based on available time
- Return ONLY valid JSON
- No markdown

Return response in this format:

{{
    "session_title": "short title tailored to mood and activity",
    "session_steps": [
        "step 1",
        "step 2",
        "step 3"
    ],
    "estimated_duration": "duration",
    "mood_addressed": "brief description of how this session addresses their mood"
}}
"""


class WellbeingService:

    def __init__(self, db: Session):

        self.db = db

        self.primary_provider = (
            llm_config.get_primary_provider()
        )

        self.fallback_provider = (
            llm_config.get_fallback_provider()
        )

    def get_available_activities(self):
        logger.debug("Returning wellbeing activities catalog")

        return {
            "activities": WELLBEING_ACTIVITIES
        }

    async def select_activity(
        self,
        user_id: str,
        activity_id: int,
        available_time_minutes: Optional[int],
        mood: Optional[str] = None,
        user_reason_for_mood: Optional[str] = None,
        custom_activity: Optional[str] = None
    ):
        logger.info(
            "Selecting activity activity_id=%s custom_activity_provided=%s",
            activity_id,
            bool(custom_activity),
        )

        if activity_id == 0:
            if not custom_activity or not custom_activity.strip():
                raise ValueError("activity_id 0 requires custom_activity")

            activity_name = custom_activity.strip()
        else:
            selected_activity = next(
                (
                    activity
                    for activity in WELLBEING_ACTIVITIES
                    if activity["activity_id"] == activity_id
                ),
                None
            )

            if not selected_activity:
                raise ValueError("Invalid activity_id")

            activity_name = (
                selected_activity["activity_name"]
            )

        # Fetch user's recent feedback to personalize the new session
        past_feedback_summary = self._build_past_feedback_summary(user_id)

        # Generate AI Session
        ai_response = await self._generate_session(
            activity_name=activity_name,
            available_time_minutes=available_time_minutes,
            mood=mood,
            user_reason_for_mood=user_reason_for_mood,
            custom_activity=custom_activity,
            past_feedback=past_feedback_summary,
        )

        # Save to DB
        saved_record = (
            repository.save_user_activity_selection(
                db=self.db,

                user_id=user_id,

                activity_id=activity_id,

                activity_name=activity_name,

                available_time_minutes=(
                    available_time_minutes
                ),

                ai_session_title=(
                    ai_response.get(
                        "session_title"
                    )
                ),

                ai_session_steps=(
                    ai_response.get(
                        "session_steps"
                    )
                ),

                ai_estimated_duration=(
                    ai_response.get(
                        "estimated_duration"
                    )
                ),
                llm_provider=(
                    ai_response.get(
                        "provider_used"
                    )
                ),
                user_reason_for_mood=user_reason_for_mood,
                custom_activity=custom_activity
            )
        )

        logger.info("Wellbeing session generated and saved")
        return {
            "message": (
                "Session generated successfully"
            ),
            "activity_name": activity_name,
            "available_time_minutes": (
                available_time_minutes
            ),
            "session_plan": {
                "session_title": (
                    ai_response.get(
                        "session_title"
                    )
                ),
                "session_steps": (
                    ai_response.get(
                        "session_steps"
                    )
                ),
                "estimated_duration": (
                    ai_response.get(
                        "estimated_duration"
                    )
                ),
                "provider_used": (
                    ai_response.get(
                        "provider_used"
                    )
                ),
                "mood_addressed": (
                    ai_response.get(
                        "mood_addressed"
                    )
                )
            },
            "database_id": saved_record.id
        }

    def _build_past_feedback_summary(self, user_id: str) -> str:
        """
        Build a compact, prompt-friendly summary of the user's recent feedback.
        Returns "No prior feedback" if none exists.
        """
        try:
            recent = repository.get_recent_feedback_for_prompt(
                db=self.db, user_id=user_id, limit=5
            )
        except Exception:
            logger.exception("Could not load recent feedback; proceeding without it")
            recent = []

        if not recent:
            return "No prior feedback"

        lines = []
        for item in recent:
            rating = item.get("rating")
            rating_str = f"{rating}/5" if rating is not None else "no rating"
            activity = item.get("activity_name") or "unknown activity"
            text = (item.get("feedback_text") or "").strip().replace("\n", " ")
            if len(text) > 160:
                text = text[:157] + "..."
            lines.append(f"- {activity} ({rating_str}): {text}")
        return "\n".join(lines)

    async def _generate_session(
        self,
        activity_name: str,
        available_time_minutes: Optional[int],
        mood: Optional[str] = None,
        user_reason_for_mood: Optional[str] = None,
        custom_activity: Optional[str] = None,
        past_feedback: str = "No prior feedback",
    ):

        # Try Primary Provider
        result = await self._try_llm_request(
            provider=self.primary_provider,
            activity_name=activity_name,
            mood=mood,
            available_time=available_time_minutes,
            user_reason_for_mood=user_reason_for_mood,
            custom_activity=custom_activity,
            past_feedback=past_feedback,
        )

        if result:

            result["provider_used"] = (
                self.primary_provider.value
            )

            return result

        logger.warning(
            "Primary provider failed. "
            "Trying fallback provider."
        )

        # Try Fallback Provider
        result = await self._try_llm_request(
            provider=self.fallback_provider,
            activity_name=activity_name,
            mood=mood,
            available_time=available_time_minutes,
            user_reason_for_mood=user_reason_for_mood,
            custom_activity=custom_activity,
            past_feedback=past_feedback,
        )

        if result:

            result["provider_used"] = (
                self.fallback_provider.value
            )

            return result

        logger.error(
            "Both providers failed."
        )

        # Default Response
        return {
            "session_title": (
                "Basic Relaxation"
            ),
            "session_steps": [
                "Sit comfortably",
                "Take deep breaths",
                "Relax your shoulders",
                "Focus on calm breathing"
            ],
            "estimated_duration": (
                f"{available_time_minutes or 5} minutes"
            ),
            "provider_used": "default",
            "mood_addressed": "Generic calming techniques"
        }

    async def _try_llm_request(
        self,
        provider: LLMProvider,
        activity_name: str,
        available_time: Optional[int],
        mood: Optional[str] = None,
        user_reason_for_mood: Optional[str] = None,
        custom_activity: Optional[str] = None,
        past_feedback: str = "No prior feedback",
    ):

        try:

            if provider == LLMProvider.GEMINI:

                return await self._call_gemini(
                    activity_name=activity_name,
                    available_time=available_time,
                    mood=mood,
                    user_reason_for_mood=user_reason_for_mood,
                    custom_activity=custom_activity,
                    past_feedback=past_feedback,
                )

            if provider == LLMProvider.GROQ:

                return await self._call_groq(
                    activity_name=activity_name,
                    available_time=available_time,
                    mood=mood,
                    user_reason_for_mood=user_reason_for_mood,
                    custom_activity=custom_activity,
                    past_feedback=past_feedback,
                )

            if provider == LLMProvider.OLLAMA:

                return await self._call_ollama(
                    activity_name=activity_name,
                    available_time=available_time,
                    mood=mood,
                    user_reason_for_mood=user_reason_for_mood,
                    custom_activity=custom_activity,
                    past_feedback=past_feedback,
                )

            return None

        except Exception:
            logger.exception("LLM provider call failed for wellbeing session")

            return None

    async def _call_gemini(

    self,
    activity_name: str,
    available_time: Optional[int],
    mood: Optional[str] = None,
    user_reason_for_mood: Optional[str] = None,
    custom_activity: Optional[str] = None,
    past_feedback: str = "No prior feedback",

    ):

        logger.debug("Calling Gemini for wellbeing session generation")
        config = llm_config.gemini

        prompt = WELLBEING_SESSION_PROMPT.format(
            mood=mood or "Not specified",
            user_reason=(user_reason_for_mood or "Not provided"),
            custom_activity=(custom_activity or "None"),
            activity_name=activity_name,
            available_time=(
                f"{available_time} minutes"
                if available_time
                else "Flexible"
            ),
            past_feedback=past_feedback,
        )

        async with httpx.AsyncClient(
            timeout=config.timeout
        ) as client:

            response = await client.post(
                f"{config.base_url}/chat/completions",
                headers={
                    "Authorization":
                    f"Bearer {config.api_key}"
                },
                json={
                    "model": config.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3
                }
            )

            if response.status_code != 200:

                logger.error(
                    f"Gemini Error: "
                    f"{response.status_code} "
                    f"{response.text}"
                )

                return None

            data = response.json()

            response_text = (
                data["choices"][0]
                ["message"]["content"]
            )

            parsed = self._parse_response(
                response_text
            )

            if parsed:
                parsed["provider_used"] = (
                    LLMProvider.GEMINI.value
                )

            return parsed

    async def _call_groq(
        self,
        activity_name: str,
        available_time: Optional[int] = None,
        mood: Optional[str] = None,
        user_reason_for_mood: Optional[str] = None,
        custom_activity: Optional[str] = None,
        past_feedback: str = "No prior feedback",
    ):

        logger.debug("Calling Groq for wellbeing session generation")
        config = llm_config.groq

        prompt = WELLBEING_SESSION_PROMPT.format(
            mood=mood or "Not specified",
            user_reason=(user_reason_for_mood or "Not provided"),
            custom_activity=(custom_activity or "None"),
            activity_name=activity_name,
            available_time=(
                f"{available_time} minutes"
                if available_time
                else "Flexible"
            ),
            past_feedback=past_feedback,
        )

        async with httpx.AsyncClient(
            timeout=config.timeout
        ) as client:

            response = await client.post(
                f"{config.base_url}/chat/completions",
                headers={
                    "Authorization":
                    f"Bearer {config.api_key}"
                },
                json={
                    "model": config.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3
                }
            )

            if response.status_code != 200:

                logger.error(
                    f"Groq Error: "
                    f"{response.status_code} "
                    f"{response.text}"
                )

                return None

            data = response.json()

            response_text = (
                data["choices"][0]
                ["message"]["content"]
            )

            return self._parse_response(
                response_text
            )

    async def _call_ollama(
        self,
        activity_name: str,
        mood: Optional[str] = None,
        available_time: Optional[int] = None,
        user_reason_for_mood: Optional[str] = None,
        custom_activity: Optional[str] = None,
        past_feedback: str = "No prior feedback",
    ):

        logger.debug("Calling Ollama for wellbeing session generation")
        config = llm_config.ollama

        prompt = WELLBEING_SESSION_PROMPT.format(
            mood=mood or "Not specified",
            user_reason=(user_reason_for_mood or "Not provided"),
            custom_activity=(custom_activity or "None"),
            activity_name=activity_name,
            available_time=(
                f"{available_time} minutes"
                if available_time
                else "Flexible"
            ),
            past_feedback=past_feedback,
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
                            "content": prompt
                        }
                    ],
                    "stream": False
                }
            )

            if response.status_code != 200:

                logger.error(
                    f"Ollama Error: "
                    f"{response.status_code} "
                    f"{response.text}"
                )

                return None

            data = response.json()

            response_text = data["choices"][0]["message"]["content"]

            return self._parse_response(
                response_text
            )

    def _parse_response(
        self,
        response_text: str
    ):

        try:

            response_text = (
                response_text
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            parsed = json.loads(
                response_text
            )

            return {
                "session_title": (
                    parsed.get(
                        "session_title"
                    )
                ),
                "session_steps": (
                    parsed.get(
                        "session_steps"
                    )
                ),
                "estimated_duration": (
                    parsed.get(
                        "estimated_duration"
                    )
                ),
                "mood_addressed": (
                    parsed.get(
                        "mood_addressed"
                    )
                )
            }

        except Exception:
            logger.exception("Failed to parse wellbeing session response")

            return None
