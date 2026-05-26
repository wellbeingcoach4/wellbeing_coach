"""
User History & Periodic Mood Analysis APIs - Documentation
============================================================

This document provides comprehensive documentation for the two new APIs
added to the Wellbeing Coach application:
1. User History API - Fetch complete user history
2. Periodic Mood Analysis API - Analyze mood trends over a date range

## Table of Contents
1. Overview
2. API Endpoints
3. Architecture
4. Usage Examples
5. Database Schema
6. Response Models
7. Error Handling

---

## 1. Overview

The User History and Periodic Mood Analysis APIs provide endpoints to:

### User History API
- Retrieve all historical data for a user in one request
- Includes mood analyses, feedback submissions, and activity selections
- Useful for generating user dashboards and comprehensive profiles

### Periodic Mood Analysis API
- Analyze mood patterns over a specific date range
- Calculate mood statistics and distributions
- Generate AI-powered insights and recommendations
- Help identify emotional trends and patterns

Both APIs follow the modular architecture pattern of the application:
- **Routes Layer**: Handle HTTP requests/responses
- **Service Layer**: Business logic and data aggregation
- **Repository Layer**: Database queries and persistence
- **Schema Layer**: Pydantic models for validation

---

## 2. API Endpoints

### Endpoint 1: Fetch User History

**URL:** `GET /user/{user_id}/history`

**Description:** Fetch complete user history including moods, feedback, and activities

**Path Parameters:**
- `user_id` (string, required): Unique user identifier
  - Format: Alphanumeric with hyphens/underscores
  - Example: "user123", "john-doe", "user_456"

**Request Example:**
```bash
curl -X GET "http://localhost:8000/user/user123/history"
```

**Response (200 OK):**
```json
{
    "user_id": "user123",
    "mood_history": [
        {
            "id": 1,
            "user_id": "user123",
            "mood_analysed": "happy",
            "reason_for_mood": "Had a great day at work",
            "confidence_score": 0.95,
            "llm_provider": "ollama",
            "created_at": "2024-01-20T10:30:00",
            "input_text": "I completed my project successfully"
        },
        {
            "id": 2,
            "user_id": "user123",
            "mood_analysed": "calm",
            "reason_for_mood": "Relaxing evening",
            "confidence_score": 0.88,
            "llm_provider": "ollama",
            "created_at": "2024-01-21T18:45:00",
            "input_text": "Spent time with family"
        }
    ],
    "feedback_history": [
        {
            "id": 1,
            "user_id": "user123",
            "feedback_text": "Great mindfulness session",
            "rating": 5,
            "created_at": "2024-01-20T11:00:00"
        }
    ],
    "activity_history": [
        {
            "id": 1,
            "user_id": "user123",
            "activity_id": 1,
            "activity_name": "Meditation",
            "available_time_minutes": 30,
            "ai_session_title": "10-minute breathing exercise",
            "ai_estimated_duration": "10 minutes",
            "created_at": "2024-01-20T08:00:00"
        }
    ],
    "total_moods": 2,
    "total_feedback": 1,
    "total_activities": 1
}
```

**Possible Errors:**
- `400 Bad Request`: Invalid user_id format
- `500 Internal Server Error`: Database query failed

---

### Endpoint 2: Fetch Periodic Mood Analysis

**URL:** `GET /user/{user_id}/mood/periodic`

**Description:** Analyze user's mood for a specific date range with AI-powered insights

**Path Parameters:**
- `user_id` (string, required): Unique user identifier

**Query Parameters:**
- `from_date` (datetime, required): Start date (ISO format)
  - Format: "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS"
  - Example: "2024-01-01" or "2024-01-01T00:00:00"
- `to_date` (datetime, required): End date (ISO format)
  - Format: "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS"
  - Example: "2024-01-31" or "2024-01-31T23:59:59"

**Request Examples:**
```bash
# Using date format
curl -X GET "http://localhost:8000/user/user123/mood/periodic?from_date=2024-01-01&to_date=2024-01-31"

# Using datetime format
curl -X GET "http://localhost:8000/user/user123/mood/periodic?from_date=2024-01-01T00:00:00&to_date=2024-01-31T23:59:59"
```

**Response (200 OK):**
```json
{
    "user_id": "user123",
    "from_date": "2024-01-01T00:00:00",
    "to_date": "2024-01-31T23:59:59",
    "moods_in_period": [
        {
            "id": 1,
            "mood_analysed": "happy",
            "reason_for_mood": "Completed project",
            "confidence_score": 0.95,
            "created_at": "2024-01-15T10:30:00"
        },
        {
            "id": 2,
            "mood_analysed": "calm",
            "reason_for_mood": "Meditation session",
            "confidence_score": 0.88,
            "created_at": "2024-01-20T18:45:00"
        },
        {
            "id": 3,
            "mood_analysed": "stressed",
            "reason_for_mood": "Deadline approaching",
            "confidence_score": 0.82,
            "created_at": "2024-01-25T14:00:00"
        }
    ],
    "mood_statistics": {
        "total_moods": 3,
        "mood_distribution": {
            "happy": 1,
            "calm": 1,
            "stressed": 1
        },
        "average_confidence": 0.883,
        "most_common_mood": "happy",
        "least_common_mood": "stressed"
    },
    "period_analysis": "Your mood has been relatively balanced throughout the month. You experienced happiness when completing significant projects, maintained calmness during relaxation periods, and showed expected stress when facing deadlines. The variation suggests healthy emotional responses to different situations.",
    "recommendation": "Continue engaging in the meditation practices that helped you achieve calm states. Consider implementing stress management techniques when approaching deadlines, such as breaking tasks into smaller parts and taking regular breaks to maintain emotional balance."
}
```

**Possible Errors:**
- `400 Bad Request`: Invalid user_id or date range (from_date > to_date)
- `404 Not Found`: No moods found in the period
- `500 Internal Server Error`: Database query or LLM analysis failed

---

## 3. Architecture

### Modular Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Routes Layer                             │
│         user_history_routes.py                              │
│  - HTTP request handling                                    │
│  - Input validation                                         │
│  - Error mapping to HTTP responses                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                            │
│         user_history_service.py                             │
│  - Business logic                                           │
│  - Data aggregation                                         │
│  - LLM integration                                          │
│  - Mood statistics calculation                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Repository Layer                         │
│         repository.py                                       │
│  - Database queries                                         │
│  - Data retrieval                                           │
│  - Transaction management                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database Layer                           │
│  - PostgreSQL                                               │
│  - Tables: mood_analysis, user_feedback,                    │
│    user_activity_selection                                  │
└─────────────────────────────────────────────────────────────┘
```

### Flow Diagrams

**User History Flow:**
```
HTTP Request
    ↓
Routes Layer (validates user_id)
    ↓
Service Layer (aggregates data)
    ├─→ Repository (get_user_moods)
    ├─→ Repository (get_user_feedback)
    └─→ Repository (get_user_activities)
    ↓
Combine results
    ↓
HTTP Response
```

**Periodic Mood Flow:**
```
HTTP Request (with date range)
    ↓
Routes Layer (validates user_id & dates)
    ↓
Service Layer
    ├─→ Repository (get_user_moods_in_period)
    ├─→ Calculate statistics
    └─→ LLM Service (generate analysis)
    ↓
Combine all results
    ↓
HTTP Response
```

---

## 4. Usage Examples

### Python with Requests Library

```python
import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

# Example 1: Fetch user history
def fetch_user_history(user_id):
    response = requests.get(f"{BASE_URL}/user/{user_id}/history")
    if response.status_code == 200:
        history = response.json()
        print(f"Total moods: {history['total_moods']}")
        print(f"Total feedback: {history['total_feedback']}")
        return history
    else:
        print(f"Error: {response.status_code}")
        print(response.json())

# Example 2: Fetch periodic mood analysis
def fetch_periodic_mood(user_id, days=30):
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)
    
    params = {
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat()
    }
    
    response = requests.get(
        f"{BASE_URL}/user/{user_id}/mood/periodic",
        params=params
    )
    
    if response.status_code == 200:
        mood_data = response.json()
        print(f"Most common mood: {mood_data['mood_statistics']['most_common_mood']}")
        print(f"Average confidence: {mood_data['mood_statistics']['average_confidence']}")
        print(f"Recommendation: {mood_data['recommendation']}")
        return mood_data
    else:
        print(f"Error: {response.status_code}")
        print(response.json())

# Usage
history = fetch_user_history("user123")
mood_analysis = fetch_periodic_mood("user123", days=30)
```

### FastAPI Client

```python
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from app.main import app

client = TestClient(app)

# Fetch history
response = client.get("/user/user123/history")
assert response.status_code == 200
history = response.json()

# Fetch periodic mood
from_date = datetime(2024, 1, 1)
to_date = datetime(2024, 1, 31)

response = client.get(
    "/user/user123/mood/periodic",
    params={
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat()
    }
)
assert response.status_code == 200
mood_data = response.json()
```

---

## 5. Database Schema

### Tables Used

#### mood_analysis
```sql
CREATE TABLE mood_analysis (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    input_text TEXT NOT NULL,
    mood_analysed VARCHAR(100) NOT NULL,
    reason_for_mood TEXT NOT NULL,
    confidence_score FLOAT,
    llm_provider VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);
```

#### user_feedback
```sql
CREATE TABLE user_feedback (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    feedback_text TEXT NOT NULL,
    rating INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
);
```

#### user_activity_selection
```sql
CREATE TABLE user_activity_selection (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    activity_id INTEGER NOT NULL,
    activity_name VARCHAR NOT NULL,
    available_time_minutes INTEGER,
    ai_session_title TEXT,
    ai_session_steps JSON,
    ai_estimated_duration VARCHAR,
    llm_provider VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. Response Models

### UserHistoryResponse

All mood, feedback, and activity records for a user.

**Fields:**
- `user_id`: String - User identifier
- `mood_history`: List[MoodHistoryItem] - All mood records
- `feedback_history`: List[FeedbackHistoryItem] - All feedback records
- `activity_history`: List[ActivityHistoryItem] - All activity records
- `total_moods`: Integer - Count of moods
- `total_feedback`: Integer - Count of feedback
- `total_activities`: Integer - Count of activities

### PeriodicMoodResponse

Mood analysis for a specific date range with statistics and AI insights.

**Fields:**
- `user_id`: String - User identifier
- `from_date`: DateTime - Period start date
- `to_date`: DateTime - Period end date
- `moods_in_period`: List[PeriodicMoodItem] - Mood records in period
- `mood_statistics`: MoodStatistics - Statistical summary
- `period_analysis`: String - AI-generated analysis
- `recommendation`: String - AI-generated recommendation

### MoodStatistics

Statistical summary of moods in a period.

**Fields:**
- `total_moods`: Integer - Count of moods
- `mood_distribution`: Dict - Distribution of mood types
- `average_confidence`: Float - Mean confidence score
- `most_common_mood`: String - Most frequent mood
- `least_common_mood`: String - Least frequent mood

---

## 7. Error Handling

Both APIs implement comprehensive error handling:

### Common Errors

| Status Code | Error | Cause | Solution |
|-------------|-------|-------|----------|
| 400 | Bad Request | Invalid user_id format | Use alphanumeric user IDs with hyphens/underscores |
| 400 | Bad Request | from_date > to_date | Ensure from_date is before to_date |
| 404 | Not Found | User not found | Check user_id is correct |
| 500 | Internal Server Error | Database error | Check database connection |
| 500 | Internal Server Error | LLM service error | Check LLM provider configuration |

### Error Response Format

```json
{
    "detail": "Error description message"
}
```

---

## 8. Performance Considerations

1. **Database Indexing**: Queries on user_id and created_at use indexes for performance
2. **Date Range Limiting**: Clients should implement reasonable date ranges (e.g., not more than 1 year)
3. **Caching**: Consider caching periodic mood analyses that haven't changed
4. **Pagination**: For large history sets, consider implementing pagination in future versions

---

## 9. Future Enhancements

Possible improvements for future versions:

1. **Pagination**: Add limit/offset parameters for large result sets
2. **Filtering**: Allow filtering mood history by mood type or confidence range
3. **Comparison**: Compare moods between two periods
4. **Export**: Export history in CSV or PDF format
5. **Custom Date Ranges**: Pre-defined ranges (last 7 days, last month, etc.)
6. **Mood Trends**: Calculate trend analysis (improving/declining)

---

## 10. Testing

Run tests with:

```bash
pytest tests/test_user_history.py -v
```

Test coverage includes:
- User history retrieval (success and empty cases)
- Periodic mood analysis (valid and invalid date ranges)
- Mood statistics calculation
- Data formatting for LLM
- Schema validation
"""

