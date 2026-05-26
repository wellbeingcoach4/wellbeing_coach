# Mood Analysis Endpoint - Quick Reference

## Endpoint URL
```
POST /mood/analyze_mood
```

## Request Schema

### MoodRequest
```json
{
  "user_id": "string (required)",
  "text": "string (required)",
  "user_reason_for_mood": "string (optional)",
  "custom_activity": "string (optional)"
}
```

### Field Details

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `user_id` | string | Yes | Alphanumeric, hyphens, underscores | Unique user identifier |
| `text` | string | Yes | Min 1 character | Text to analyze for mood |
| `user_reason_for_mood` | string | No | Min 1, Max 500 chars | User's own reason for their mood |
| `custom_activity` | string | No | Min 3, Max 255 chars | Custom activity if not selecting from suggestions |

## Response Schema

### MoodResponse
```json
{
  "mood_analysed": "string",
  "reason_for_mood": "string",
  "constructive_suggestion": "string",
  "confidence_score": 0.0-1.0,
  "llm_provider": "string",
  "database_id": "integer or null"
}
```

### Response Field Details

| Field | Type | Description |
|-------|------|-------------|
| `mood_analysed` | string | Detected mood (e.g., happy, sad, angry, anxious, neutral) |
| `reason_for_mood` | string | AI-generated explanation for the mood |
| `constructive_suggestion` | string | Actionable suggestion to manage/improve the mood |
| `confidence_score` | float | Confidence level of analysis (0-1) |
| `llm_provider` | string | Provider used (ollama, groq, gemini, or default) |
| `database_id` | integer | Database record ID for tracking |

## Usage Examples

### Example 1: Basic Usage (Backward Compatible)
```bash
curl -X POST http://localhost:8000/mood/analyze_mood \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "text": "I am feeling great today!"
  }'
```

**Response:**
```json
{
  "mood_analysed": "happy",
  "reason_for_mood": "The positive language and exclamation mark indicate enthusiasm and joy.",
  "constructive_suggestion": "Continue this positive momentum by engaging in activities you enjoy and sharing this happiness with others.",
  "confidence_score": 0.95,
  "llm_provider": "groq",
  "database_id": 101
}
```

### Example 2: With User's Reason for Mood
```bash
curl -X POST http://localhost:8000/mood/analyze_mood \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user456",
    "text": "I have been so stressed lately",
    "user_reason_for_mood": "Too many deadlines at work and family responsibilities"
  }'
```

**Response:**
```json
{
  "mood_analysed": "anxious",
  "reason_for_mood": "The text expresses stress, combined with the user mentioning workload and family pressures indicates anxiety about managing multiple responsibilities.",
  "constructive_suggestion": "Break your tasks into smaller, manageable steps. Prioritize what's most important and delegate if possible. Consider scheduling specific times for work and family - this separation can reduce mental load.",
  "confidence_score": 0.92,
  "llm_provider": "groq",
  "database_id": 102
}
```

### Example 3: With Custom Activity
```bash
curl -X POST http://localhost:8000/mood/analyze_mood \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user789",
    "text": "Feeling unmotivated and disconnected",
    "custom_activity": "Photography walks in nature"
  }'
```

**Response:**
```json
{
  "mood_analysed": "sad",
  "reason_for_mood": "The text indicates low motivation and emotional disconnection, suggesting low mood.",
  "constructive_suggestion": "Consider taking photography walks in nature - the combination of movement, creative expression, and natural exposure can significantly boost mood. Start with just 20-30 minutes to ease back into activity.",
  "confidence_score": 0.88,
  "llm_provider": "groq",
  "database_id": 103
}
```

### Example 4: Complete Usage (All Fields)
```bash
curl -X POST http://localhost:8000/mood/analyze_mood \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user999",
    "text": "I feel frustrated but ready to make changes",
    "user_reason_for_mood": "Failed project at work but determined to learn from it",
    "custom_activity": "Online courses and skill development"
  }'
```

**Response:**
```json
{
  "mood_analysed": "frustrated",
  "reason_for_mood": "The user expresses frustration about failure, but also shows determination and readiness for improvement, indicating mixed emotions leaning toward frustration.",
  "constructive_suggestion": "Channel this frustration into learning through online courses. Breaking down the learning into manageable modules will help you regain confidence. Celebrate small wins in your learning journey - this will reinforce your determination.",
  "confidence_score": 0.89,
  "llm_provider": "groq",
  "database_id": 104
}
```

## Key Features

### ✅ What's Supported
- ✓ User can provide reason for their mood
- ✓ User can suggest custom activities
- ✓ Automatic generation of constructive suggestions
- ✓ Multi-provider LLM support (ollama, groq, gemini)
- ✓ Fallback to default response if all providers fail
- ✓ Validation of all inputs
- ✓ Secure prevention of activity_id injection

### ❌ What's NOT Supported
- ✗ `activity_id` in request (intentionally blocked for accuracy)
- ✗ Multiple moods in one request
- ✗ Real-time streaming responses

## Important Notes

### Security & Validation
1. **activity_id Prevention**: The endpoint explicitly prevents users from including `activity_id` in their requests to ensure mood analysis accuracy
2. **Field Validation**:
   - `custom_activity` must be at least 3 characters long
   - `user_reason_for_mood` cannot be empty if provided
   - All string fields are trimmed of whitespace
3. **Input Limits**:
   - `user_reason_for_mood`: Max 500 characters
   - `custom_activity`: Max 255 characters

### LLM Provider Fallback
If the primary LLM provider fails:
1. Attempts fallback provider
2. If both fail, returns default response with helpful guidance
3. All attempts are logged for debugging

### Data Storage
- All fields are stored in database for history tracking
- User's perspective stored alongside AI analysis
- Custom activities tracked for future reference
- Constructive suggestions stored for pattern analysis

## Error Handling

### Validation Errors (422)
```json
{
  "detail": [
    {
      "loc": ["body", "custom_activity"],
      "msg": "custom_activity must be at least 3 characters long",
      "type": "value_error"
    }
  ]
}
```

### Server Errors (500)
The endpoint returns a default response with neutral mood and helpful message instead of failing completely.

## Performance Tips

1. **Shorter text analysis is faster**: While any length is supported, concise input (100-500 chars) typically gets faster responses
2. **Custom activity field helps accuracy**: More context = better suggestions
3. **User reason field is optional**: Use it only when it adds relevant context

## Integration Guide

### Python/FastAPI
```python
from httpx import AsyncClient

async def analyze_user_mood():
    async with AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/mood/analyze_mood",
            json={
                "user_id": "user123",
                "text": "I'm feeling mixed emotions today",
                "user_reason_for_mood": "Excited about new opportunity but nervous",
                "custom_activity": "Meditation and yoga"
            }
        )
        return response.json()
```

### JavaScript/Node.js
```javascript
async function analyzeMood() {
  const response = await fetch('/mood/analyze_mood', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: 'user123',
      text: 'Feeling mixed emotions today',
      user_reason_for_mood: 'Excited about new opportunity but nervous',
      custom_activity: 'Meditation and yoga'
    })
  });
  return response.json();
}
```

## Database Schema

### mood_analysis table (new columns)
```sql
user_reason_for_mood TEXT NULL          -- User's provided reason for mood
custom_activity VARCHAR(255) NULL       -- Custom activity from user
constructive_suggestion TEXT NULL       -- AI-generated suggestion
```

## Testing Checklist

- [ ] Test with user_reason_for_mood only
- [ ] Test with custom_activity only  
- [ ] Test with both fields
- [ ] Test with neither field (backward compatibility)
- [ ] Test with activity_id in request (should be ignored)
- [ ] Test with invalid custom_activity (< 3 chars)
- [ ] Test with empty user_reason_for_mood
- [ ] Test with long text (500+ chars)
- [ ] Test provider fallback (disconnect primary provider)
- [ ] Verify database storage of all fields
