# Mood Analysis Endpoint Enhancement

## Overview
Enhanced the mood analysis endpoint to include user's reason for mood, support for custom activities, and constructive response generation with improved accuracy.

## Changes Made

### 1. **Schema Updates** (`app/schema/mood_schema.py`)

#### MoodRequest - New Fields
- **`user_reason_for_mood`** (Optional[str]): Allows users to provide their own reason for their mood
  - Validation: Max 500 characters, stripped of whitespace
  - Enhanced context for more accurate mood analysis
  
- **`custom_activity`** (Optional[str]): For users who want to add custom activities not in the suggestion list
  - Validation: Min 3 characters, max 255 characters, stripped of whitespace
  - Not required - users can leave empty if selecting from suggestions
  - Prevents activity_id input by removing it in dict() method
  
#### MoodResponse - New Fields
- **`constructive_suggestion`** (str): AI-generated constructive advice for managing the mood
  - Replaces generic responses with actionable, positive suggestions
  - Enhances user experience with practical guidance

#### Security Validations
- `@validator` decorators ensure:
  - activity_id cannot be included in requests (removed in dict() method)
  - custom_activity minimum length to prevent junk inputs
  - user_reason_for_mood cannot be empty if provided
  - All strings are stripped of leading/trailing whitespace

### 2. **Database Model Updates** (`app/database/models.py`)

#### MoodAnalysis Table - New Columns
```python
user_reason_for_mood = Column(Text, nullable=True)      # User's provided reason
custom_activity = Column(String(255), nullable=True)    # Custom activity if provided
constructive_suggestion = Column(Text, nullable=True)   # AI-generated suggestion
```

These fields allow for:
- Tracking user's own perspective on their mood
- Storing custom activities for future reference
- Recording the constructive suggestions provided to users

### 3. **Service Layer Enhancements** (`app/service/mood_analyser.py`)

#### Enhanced Prompt (`MOOD_ANALYSIS_PROMPT`)
Now requests the LLM to:
1. Generate **constructive and supportive** responses
2. Include `constructive_suggestion` field in JSON response
3. Consider user's reason for mood in analysis
4. Incorporate custom activity in suggestion if provided

**Prompt Format:**
```
- Analyzes mood and emotional state
- Validates it understands emotion context
- Generates actionable suggestions
- All responses are JSON with 3 fields:
  - mood_analysed
  - reason_for_mood
  - constructive_suggestion
```

#### `analyze_mood()` Method
- **New Parameters:**
  - `user_reason_for_mood`: Optional string
  - `custom_activity`: Optional string
  
- **Enhanced Logic:**
  1. Calls `_build_prompt_context()` to incorporate user inputs
  2. Passes prompt context to all LLM providers
  3. Stores new fields in database
  4. Returns constructive_suggestion in response

#### `_build_prompt_context()` Method (NEW)
Constructs additional prompt context:
```python
- If user_reason_for_mood provided: 
  "User's reason for their mood: {reason}"
  
- If custom_activity provided:
  "User is interested in: {activity}. Please consider this when making suggestions."
```

#### LLM Provider Methods Updated
All provider methods (`_call_ollama`, `_call_groq`, `_call_gemini`) now:
- Accept `prompt_context` parameter
- Format prompt with user-specific context
- Generate more relevant responses based on user's situation

#### Response Parsing (`_parse_llm_response()`)
- Now validates and extracts `constructive_suggestion` field
- Provides fallback suggestion if not included: 
  *"Focus on activities that bring you joy and maintain social connections."*

#### Default Response (`_get_default_response()`)
- Updated to include `constructive_suggestion` field
- Fallback message encourages self-care: 
  *"Please try again in a moment. In the meantime, consider taking a few deep breaths and stepping away briefly to refresh."*

#### Validation (`_is_valid_response()`)
- Now validates all 3 required fields:
  - mood_analysed
  - reason_for_mood
  - constructive_suggestion

### 4. **Repository Layer** (`app/database/repository.py`)

#### `save_mood_analysis()` Function
**New Parameters:**
```python
user_reason_for_mood: Optional[str] = None
custom_activity: Optional[str] = None
constructive_suggestion: Optional[str] = None
```

**Enhancements:**
- Saves all new fields to database
- Maintains backward compatibility
- All new parameters are optional

### 5. **Route Updates** (`app/route/mood_analysis_routes.py`)

#### `/analyze_mood` Endpoint
- **Updated Documentation** explaining:
  - New parameters accepted
  - How user_reason_for_mood enhances analysis
  - How custom_activity affects suggestions
  - Why activity_id is NOT accepted
  
- **Updated Implementation:**
  - Passes user_reason_for_mood to service
  - Passes custom_activity to service
  - Service returns constructive_suggestion in response

## Data Flow

```
User Request (with optional user_reason_for_mood, custom_activity)
    ↓
Route validates request (ensures no activity_id)
    ↓
Service.analyze_mood() receives user inputs
    ↓
Service builds prompt context with user inputs
    ↓
LLM receives enhanced prompt with:
  - Original text
  - User's reason for mood
  - Custom activity (if provided)
    ↓
LLM generates JSON with:
  - mood_analysed
  - reason_for_mood
  - constructive_suggestion
    ↓
Response parsed and validated (3 fields required)
    ↓
Database saves:
  - Original analysis
  - User's reason
  - Custom activity
  - Constructive suggestion
    ↓
Response returned to user with all fields + database_id
```

## Example Request/Response

### Request
```json
{
  "user_id": "user123",
  "text": "I've been feeling overwhelmed with work lately",
  "user_reason_for_mood": "Too many tasks and tight deadlines",
  "custom_activity": "Meditation and journaling"
}
```

### Response
```json
{
  "mood_analysed": "anxious",
  "reason_for_mood": "The text indicates work-related stress and feeling overwhelmed with responsibilities",
  "constructive_suggestion": "Try breaking your tasks into smaller, manageable chunks. Schedule short 10-minute meditation and journaling sessions between tasks to reset. This approach can reduce anxiety and improve productivity.",
  "confidence_score": 0.90,
  "llm_provider": "groq",
  "database_id": 42
}
```

## Validations & Security

### Input Validations
1. **user_id**: Required, alphanumeric with underscores/hyphens only
2. **text**: Required, minimum 1 character
3. **user_reason_for_mood**: Optional, max 500 chars, stripped
4. **custom_activity**: Optional, min 3 chars, max 255 chars, stripped
5. **activity_id**: EXPLICITLY PREVENTED via validator

### Output Validations
1. All three required fields must be present in LLM response
2. Fields must not be empty/None
3. Fields are trimmed of whitespace
4. Confidence score between 0-1
5. Valid LLM provider name

### Error Handling
- Failed LLM calls fallback to default response with guidance
- Both failures return neutral mood with helpful message
- All errors logged for debugging
- Database transaction rolled back on failure

## Benefits

1. **Better Context**: Users can explain their mood, leading to more accurate analysis
2. **Personalized Activities**: Custom activity field allows users to incorporate their preferences
3. **Constructive Guidance**: Response includes actionable suggestions, not just analysis
4. **Data-Driven Insights**: User's perspective stored alongside AI analysis for future patterns
5. **Improved Accuracy**: LLM has more context for generating relevant suggestions
6. **Security**: activity_id explicitly prevented, validations ensure data quality
7. **Backward Compatible**: All new fields optional, existing code continues to work

## Database Migration Required

Add the three new columns to existing mood_analysis table:
```sql
ALTER TABLE mood_analysis ADD COLUMN user_reason_for_mood TEXT NULL;
ALTER TABLE mood_analysis ADD COLUMN custom_activity VARCHAR(255) NULL;
ALTER TABLE mood_analysis ADD COLUMN constructive_suggestion TEXT NULL;
```

## Testing Recommendations

1. **Test with all combinations:**
   - user_reason_for_mood provided, custom_activity not provided
   - custom_activity provided, user_reason_for_mood not provided
   - Both provided
   - Neither provided (backward compatibility)

2. **Validate activity_id rejection:**
   - Attempt to send activity_id in request
   - Confirm it's ignored/rejected

3. **Test prompt context:**
   - Verify LLM uses user_reason_for_mood in analysis
   - Verify LLM incorporates custom_activity in suggestions

4. **Error scenarios:**
   - All LLM providers fail
   - Invalid JSON response
   - Missing required fields in LLM response

## Future Enhancements

1. Add activity history to suggest activities based on past selections
2. Track which activities helped which moods (feedback loop)
3. Add mood trend analysis
4. Provide activity recommendations based on mood patterns
5. Add habit tracking integration
