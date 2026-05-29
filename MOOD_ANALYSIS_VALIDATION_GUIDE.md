# Mood Analysis Enhancement - Validation & Testing Guide

## Request Validation Rules

### Field: user_id
```
Type: String
Required: YES
Pattern: ^[a-zA-Z0-9_-]+$
Length: Min 1
Examples:
✓ "user123"
✓ "john-doe"
✓ "alice_smith_001"
✗ "user@123" (@ not allowed)
✗ "user 123" (space not allowed)
✗ "" (empty)
```

### Field: text
```
Type: String
Required: YES
Length: Min 1, No Max
Examples:
✓ "I feel happy"
✓ "Today was really challenging. I had multiple meetings, didn't get lunch, and my project deadline moved up. I'm exhausted but trying to stay positive." (long text)
✗ "" (empty)
✗ "   " (whitespace only - will be treated as empty)
```

### Field: user_reason_for_mood
```
Type: String
Required: NO
Length: Min 1 (if provided), Max 500
Trimming: YES (automatically stripped)
Examples:
✓ NULL (not provided)
✓ "Work stress"
✓ "Got promoted at work, very excited!"
✓ "Family issues and sleep deprivation" (can be detailed)
✗ "" (empty string - will raise validation error)
✗ "   " (whitespace only - will raise validation error)
✗ "x" * 501 (exceeds 500 char limit)
```

### Field: custom_activity
```
Type: String
Required: NO
Length: Min 3, Max 255
Trimming: YES (automatically stripped)
Examples:
✓ NULL (not provided)
✓ "Yoga"
✓ "Photography and hiking"
✓ "Learning Python programming through online courses"
✗ "" (empty string)
✗ "ab" (less than 3 characters - error)
✗ "   " (whitespace only - will be treated as empty)
✗ "x" * 256 (exceeds 255 char limit)
✗ "activity_id: 5" (activity_id explicitly removed)
```

### Field: activity_id (BLOCKED)
```
Type: Not Accepted
Description: Intentionally blocked for security and accuracy
Behavior: If included in request, it will be removed by dict() method
Example:
❌ {"user_id": "user123", "text": "...", "activity_id": 5} 
   → activity_id will be stripped out before processing
```

## Response Field Details

### mood_analysed
```
Type: String
Possible Values: happy, sad, angry, anxious, neutral, frustrated, excited, 
                 calm, stressed, confused, hopeful, etc.
Examples:
- "happy"
- "anxious"
- "mixed" (if mood has multiple components)
```

### reason_for_mood
```
Type: String
Content: AI-generated explanation based on:
  1. Original text content
  2. User's reason (if provided)
  3. Custom activity context (if provided)
Examples:
- "The positive language and excitement indicated joy"
- "Work stress mentioned combined with sleep deprivation indicates anxiety"
- "User mentioned overcoming challenges with determination shows resilience"
```

### constructive_suggestion
```
Type: String
Content: Actionable, positive advice including:
  1. General mood management techniques
  2. User's custom activity (if provided)
  3. Specific to detected mood
Examples:
- "Try incorporating your photography hobby - the creative expression and 
   outdoor time can significantly improve mood"
- "Break tasks into smaller steps and schedule breaks to manage anxiety"
- "Share your excitement with others who can celebrate with you"
```

### confidence_score
```
Type: Float
Range: 0.0 to 1.0
Interpretation:
- 0.85-0.95: High confidence (LLM is certain about analysis)
- 0.75-0.85: Medium confidence (some ambiguity but clear mood)
- 0.0-0.75: Low confidence (service error or fallback)
Provider Defaults:
- Ollama: 0.85
- Groq: 0.90
- Gemini: 0.92
- Default: 0.0
```

### llm_provider
```
Type: String
Possible Values: ollama, groq, gemini, default
- ollama: Local model (attempted first)
- groq: Cloud API fallback
- gemini: Google API fallback
- default: All providers failed, returning safe response
```

### database_id
```
Type: Integer or Null
Description: Record ID in mood_analysis table
- Contains: ID if successfully saved
- Null: If save operation failed
Usage: Track analysis in database for history/patterns
```

## Validation Flow Diagram

```
POST /mood/analyze_mood
    ↓
[FastAPI validates MoodRequest]
    ├─ user_id: pattern match + non-empty
    ├─ text: non-empty
    ├─ user_reason_for_mood: if present, strip + check min length
    ├─ custom_activity: if present, strip + check min 3 chars
    └─ activity_id: REMOVED if present
    ↓
[Pass all validations?]
    ├─ NO → Return 422 Unprocessable Entity
    └─ YES ↓
    ↓
[MoodAnalyzerService.analyze_mood()]
    ├─ Build prompt context
    ├─ Call LLM (with retries)
    ├─ Parse response JSON
    ├─ Validate 3 required fields
    └─ Save to database
    ↓
[Return MoodResponse]
```

## Common Validation Errors & Solutions

### Error 1: "custom_activity must be at least 3 characters long"
```
Issue: User provided custom_activity with < 3 characters
Example Request:
{
  "user_id": "user123",
  "text": "I feel bad",
  "custom_activity": "ab"  ← Only 2 characters
}

Solution: Use activity name with at least 3 characters
{
  "user_id": "user123",
  "text": "I feel bad",
  "custom_activity": "Art"  ← 3 characters ✓
}
```

### Error 2: "user_reason_for_mood cannot be empty or whitespace only"
```
Issue: User provided empty/whitespace-only reason
Example Request:
{
  "user_id": "user123",
  "text": "I'm stressed",
  "user_reason_for_mood": "   "  ← Only whitespace
}

Solution: Either omit field or provide actual reason
{
  "user_id": "user123",
  "text": "I'm stressed",
  "user_reason_for_mood": "Tight project deadline"  ✓
}
```

### Error 3: "user_id" does not match pattern
```
Issue: user_id contains invalid characters
Example Request:
{
  "user_id": "user@123",  ← Contains @ symbol
  "text": "Hello"
}

Solution: Use only alphanumeric, hyphens, underscores
{
  "user_id": "user-123",  ← Valid ✓
  "text": "Hello"
}
```

## Edge Cases & Expected Behavior

### Edge Case 1: All Optional Fields Omitted
```
Request:
{
  "user_id": "user123",
  "text": "I'm happy"
}

Response: ✓ 200 OK
- Mood analyzed from text alone
- LLM generates generic suggestion
- No database_id if save fails
```

### Edge Case 2: activity_id Injection Attempt
```
Request:
{
  "user_id": "user123",
  "text": "Help me",
  "activity_id": 42  ← Not in schema
}

Behavior:
- FastAPI ignores extra fields by default
- activity_id is removed in dict() method
- Request proceeds as if activity_id wasn't present
- Response: ✓ 200 OK (processed normally)
```

### Edge Case 3: Very Long Text
```
Request:
{
  "user_id": "user123",
  "text": "..." * 10000  ← 30,000+ characters
}

Behavior:
- Accepted (no max length on text)
- LLM processes full text
- May take longer but returns valid response
- Response: ✓ 200 OK with full analysis
```

### Edge Case 4: Both Reason and Custom Activity
```
Request:
{
  "user_id": "user123",
  "text": "I feel motivated",
  "user_reason_for_mood": "Just completed a hard project",
  "custom_activity": "Running and outdoor activities"
}

Behavior:
- Both incorporated in prompt
- LLM generates suggestion including custom activity
- Database saves all fields
- Response: ✓ 200 OK with contextual suggestion
```

### Edge Case 5: Unicode & Special Characters in Text
```
Request:
{
  "user_id": "user_123",
  "text": "Je suis heureux 😊 ¡Muy bien! 你好",
  "custom_activity": "Yoga & meditation"
}

Behavior:
- Unicode accepted and processed
- LLM (if supports UTF-8) analyzes correctly
- Response: ✓ 200 OK with multilingual support
```

### Edge Case 6: LLM Provider Failure Scenario
```
Scenario: Ollama unavailable, Groq API down, Gemini slow
Process:
1. Try Ollama → Fails (connection timeout)
2. Try Groq → Fails (API key invalid)
3. Try Gemini → Fails (rate limit exceeded)
4. Return default response

Response: ✓ 200 OK (graceful fallback)
{
  "mood_analysed": "neutral",
  "reason_for_mood": "Unable to analyze mood due to service unavailability...",
  "constructive_suggestion": "Please try again in a moment...",
  "confidence_score": 0.0,
  "llm_provider": "default",
  "database_id": null
}
```

### Edge Case 7: Whitespace-Only Custom Activity
```
Request:
{
  "user_id": "user123",
  "text": "I'm sad",
  "custom_activity": "   "  ← Only spaces
}

Behavior:
- Trimmed to empty string → ""
- Treated as provided but empty
- Validation raises error
- Response: ✗ 422 Unprocessable Entity
```

## Testing Checklist

### ✓ Valid Requests
- [ ] Minimal request (only user_id + text)
- [ ] With user_reason_for_mood only
- [ ] With custom_activity only
- [ ] With both user_reason_for_mood and custom_activity
- [ ] With very long text
- [ ] With unicode characters
- [ ] With max-length fields (500 & 255 chars)

### ✗ Invalid Requests
- [ ] Missing user_id
- [ ] Missing text
- [ ] Empty user_id
- [ ] Empty text
- [ ] Invalid user_id pattern
- [ ] Custom activity < 3 chars
- [ ] Empty user_reason_for_mood
- [ ] user_reason_for_mood > 500 chars
- [ ] custom_activity > 255 chars
- [ ] activity_id in request (should be ignored)

### 🔄 Provider Fallback Testing
- [ ] Ollama working
- [ ] Ollama fails, Groq succeeds
- [ ] Both fail, Gemini succeeds
- [ ] All fail, default response returned

### 💾 Database Testing
- [ ] All 6 main fields saved
- [ ] user_reason_for_mood stored correctly
- [ ] custom_activity stored correctly
- [ ] constructive_suggestion stored correctly
- [ ] None of fields cause constraint violations

### 📊 Response Validation
- [ ] Confidence score in 0-1 range
- [ ] llm_provider is one of allowed values
- [ ] database_id is integer or null
- [ ] All text fields are non-empty (if not null)
- [ ] mood_analysed is single word/phrase

