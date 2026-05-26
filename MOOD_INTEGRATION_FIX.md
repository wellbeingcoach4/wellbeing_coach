# Mood Integration Fix - Pointers

## Problem Summary
The mood classified by `/mood/analyze_mood` API is not being passed to the session generation. This results in generic sessions that don't account for the user's current emotional state.

---

## Current Flow (Broken)
```
1. User calls /mood/analyze_mood → Returns mood_analysed (e.g., "anxious", "happy")
2. User calls /wellbeing/select-activity → Ignores mood, generates generic session
3. LLM generates session without mood context
```

## Required Flow (Fixed)
```
1. User calls /mood/analyze_mood → Returns mood_analysed
2. User calls /wellbeing/select-activity + passes mood → Uses mood in prompt
3. LLM generates mood-aware session
```

---

## Fix Checklist - 5 Steps

### **Step 1: Update Schema** 
**File:** `app/schema/wellbeing_schema.py`

Add `mood` parameter to `ActivitySelectionRequest`:
```python
class ActivitySelectionRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    activity_id: int
    available_time_minutes: Optional[int] = None
    mood: Optional[str] = None  # ADD THIS - e.g., "anxious", "happy", "sad"
```

---

### **Step 2: Update Prompt Template**
**File:** `app/service/wellbeing_service.py`

Replace `WELLBEING_SESSION_PROMPT` to include mood context:

```python
WELLBEING_SESSION_PROMPT = """
You are an AI wellbeing coach specializing in personalized mental health support.

Generate a personalized wellbeing session for the user based on their current emotional state and activity preference.

User's Current Mood:
{mood}

Activity Selected:
{activity_name}

User Available Time:
{available_time}

Instructions:
- Tailor the session steps specifically to address the user's current mood
- If mood is anxious: include calming, grounding techniques
- If mood is sad: include uplifting, motivational elements
- If mood is stressed: include stress-relief techniques
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
```

---

### **Step 3: Update Route Handler**
**File:** `app/route/wellbeing_routes.py`

Modify `select_activity()` route to accept and pass mood:

```python
@router.post("/select-activity", response_model=ActivitySelectionResponse)
async def select_activity(
    request: ActivitySelectionRequest,
    db: Session = Depends(get_db)
):
    try:
        service = WellbeingService(db)
        return await service.select_activity(
            user_id=request.user_id,
            activity_id=request.activity_id,
            available_time_minutes=request.available_time_minutes,
            mood=request.mood  # ADD THIS
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

### **Step 4: Update Service Methods**
**File:** `app/service/wellbeing_service.py`

**a) Update `select_activity()` method signature:**
```python
async def select_activity(
    self,
    user_id: str,
    activity_id: int,
    available_time_minutes: Optional[int],
    mood: Optional[str] = None  # ADD THIS
):
```

**b) Pass mood to `_generate_session()`:**
```python
# Generate AI Session
ai_response = await self._generate_session(
    activity_name=activity_name,
    available_time_minutes=available_time_minutes,
    mood=mood  # ADD THIS
)
```

**c) Update `_generate_session()` method:**
```python
async def _generate_session(
    self,
    activity_name: str,
    available_time_minutes: Optional[int],
    mood: Optional[str] = None  # ADD THIS
):
    # Try Primary Provider
    result = await self._try_llm_request(
        provider=self.primary_provider,
        activity_name=activity_name,
        available_time=available_time_minutes,
        mood=mood  # ADD THIS
    )
    # ... rest of the method
```

**d) Update `_try_llm_request()` method:**
```python
async def _try_llm_request(
    self,
    provider: LLMProvider,
    activity_name: str,
    available_time: Optional[int],
    mood: Optional[str] = None  # ADD THIS
):
    try:
        if provider == LLMProvider.GEMINI:
            return await self._call_gemini(
                activity_name,
                available_time,
                mood  # ADD THIS
            )
        if provider == LLMProvider.GROQ:
            return await self._call_groq(
                activity_name,
                available_time,
                mood  # ADD THIS
            )
        if provider == LLMProvider.OLLAMA:
            return await self._call_ollama(
                activity_name,
                available_time,
                mood  # ADD THIS
            )
        return None
    except Exception as e:
        logger.error(f"LLM Provider Error: {str(e)}")
        return None
```

---

### **Step 5: Update LLM Call Methods**
**File:** `app/service/wellbeing_service.py`

Update all three LLM provider methods to include mood:

**For `_call_gemini()`:**
```python
async def _call_gemini(
    self,
    activity_name: str,
    available_time: Optional[int],
    mood: Optional[str] = None  # ADD THIS
):
    config = llm_config.gemini
    
    prompt = WELLBEING_SESSION_PROMPT.format(
        mood=mood or "Not specified",  # ADD THIS
        activity_name=activity_name,
        available_time=(
            f"{available_time} minutes"
            if available_time
            else "Flexible"
        )
    )
    # ... rest remains same
```

**Same pattern for `_call_groq()` and `_call_ollama()`** - add the `mood` parameter and include it in the prompt formatting.

---

### **Step 6: Update Response Schema** (Optional but Recommended)
**File:** `app/schema/wellbeing_schema.py`

Add mood-aware field to response:
```python
class SessionPlanResponse(BaseModel):
    session_title: str
    session_steps: List[str]
    estimated_duration: str
    provider_used: str
    mood_addressed: Optional[str] = None  # ADD THIS
```

---

## Usage Example After Fix

```bash
# Step 1: Analyze mood
curl -X POST http://localhost:8000/mood/analyze_mood \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "text": "I feel really stressed about my upcoming presentation"}'

# Response: {"mood_analysed": "anxious", "reason_for_mood": "...", ...}

# Step 2: Select activity with mood context
curl -X POST http://localhost:8000/wellbeing/select-activity \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "activity_id": 1,
    "available_time_minutes": 15,
    "mood": "anxious"
  }'

# Response: Session tailored to anxiety with calming techniques
```

---

## Key Benefits After Fix
✅ Sessions are mood-aware and contextual
✅ LLM can suggest appropriate coping techniques for the current mood
✅ Better user experience with personalized guidance
✅ Each mood gets targeted intervention (anxious → grounding, sad → uplifting, etc.)
