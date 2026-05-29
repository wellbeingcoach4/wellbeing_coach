from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class WellbeingActivityResponse(BaseModel):

    activity_id: int

    activity_name: str

    description: str


class WellbeingActivitiesListResponse(BaseModel):

    activities: List[WellbeingActivityResponse]


class ActivitySelectionRequest(BaseModel):

    user_id: str = Field(...,min_length=1, pattern=r"^[a-zA-Z0-9_-]+$",
    description="Unique identifier for the user")

    activity_id: int

    available_time_minutes: Optional[int] = Field(None, description="Available time in minutes for the activity")

    mood: Optional[str] = None

    user_reason_for_mood: Optional[str] = Field(None,max_length=500,description="User's reason for their current mood")

    custom_activity: Optional[str] = Field(None,min_length=3,max_length=255,
    description="Custom activity provided by user if not selecting from suggestions")

    @field_validator("custom_activity", mode="before")
    @classmethod
    def _normalize_custom_activity(cls, value):
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        return cleaned if cleaned else None

    @field_validator("user_reason_for_mood", mode="before")
    @classmethod
    def _escape_double_quotes(cls, value):
        """Escape double quotes in user-supplied reason text.

        The value is interpolated into LLM prompts; bare double quotes can
        break downstream JSON formatting or invite prompt injection.
        Backslashes are also escaped first to keep the escape well-formed.
        Whitespace-only input is normalized to None.
        """
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        if not cleaned:
            return None
        cleaned = cleaned.replace("\\", "\\\\").replace('"', '\\"')
        return cleaned

    @model_validator(mode="after")
    def validate_custom_activity_with_zero_id(self):

        if self.custom_activity:
            if self.activity_id != 0:
                raise ValueError(
                    "custom_activity requires activity_id 0"
                )
        elif self.activity_id == 0:
            raise ValueError(
                "Provide either a predefined activity_id or custom_activity "
                "so the session context is clear"
            )

        return self

class SessionPlanResponse(BaseModel):

    session_title: str

    session_steps: List[str]

    estimated_duration: str

    provider_used: str

    mood_addressed: Optional[str] = None

    @field_validator("estimated_duration", mode="before")
    @classmethod
    def _coerce_duration_to_str(cls, value):
        """LLMs sometimes return a bare number (e.g. 40) for duration.

        Coerce numeric values to a "<N> minutes" string so the response
        schema validation does not fail on otherwise-valid sessions.
        """
        if isinstance(value, (int, float)):
            return f"{int(value)} minutes"
        return value


class ActivitySelectionResponse(BaseModel):

    message: str

    activity_name: str

    available_time_minutes: Optional[int]

    session_plan: (SessionPlanResponse)

    database_id: int
