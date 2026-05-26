# Quick Reference Guide

## File Structure Created

```
app/
├── __init__.py                                  # Package init with exports
├── main.py                                      # FastAPI app (UPDATED)
├── database/
│   ├── __init__.py                             # Exports
│   ├── models.py                               # MoodAnalysis SQLAlchemy model
│   └── connection.py                           # PostgreSQL connection
├── llm/
│   ├── __init__.py                             # Exports
│   └── config.py                               # LLM provider configuration
├── route/
│   └── mood_analysis.py                        # API endpoints (UPDATED)
├── schema/
│   └── mood_schema                             # Pydantic models (UPDATED)
├── service/
│   ├── __init__.py                             # Exports
│   └── mood_analyser.py                        # Mood analysis service (NEW)
└── tests/
    ├── __init__.py                             # Test package init
    └── test_mood_analyzer.py                   # Service tests
```

## Key Files

| File | Purpose |
|------|---------|
| `app/service/mood_analyser.py` | Main mood analysis service with LLM fallback |
| `app/database/models.py` | MoodAnalysis database model |
| `app/database/connection.py` | PostgreSQL connection management |
| `app/llm/config.py` | LLM provider configuration (Ollama/Groq/Gemini) |
| `app/main.py` | FastAPI application entry point |
| `app/route/mood_analysis.py` | API endpoints |
| `SETUP.md` | Complete setup instructions |
| `IMPLEMENTATION_SUMMARY.md` | This implementation summary |

## Environment Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup PostgreSQL
createdb wellbeing_coach

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Setup LLM provider (choose one)
ollama serve                    # For Ollama
# Or get API keys from Groq/Gemini

# 5. Run application
python app/main.py
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/mood/analyze_mood` | POST | Analyze mood from text |
| `/mood/mood_history/{user_id}` | GET | Get user's mood history |
| `/docs` | GET | Swagger API documentation |
| `/redoc` | GET | ReDoc API documentation |

## Request Examples

### Analyze Mood
```bash
curl -X POST "http://localhost:8000/mood/analyze_mood" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "text": "I am feeling overwhelmed with work"
  }'
```

### Get Mood History
```bash
curl "http://localhost:8000/mood/mood_history/user123?limit=10"
```

## Response Format

```json
{
    "mood_analysed": "anxious",
    "reason_for_mood": "Expression shows worry and stress",
    "confidence_score": 0.87,
    "llm_provider": "ollama",
    "database_id": 1
}
```

## Database Schema

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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Environment Variables

```
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/wellbeing_coach

# LLM Providers
LLM_PROVIDER=ollama              # Primary
LLM_FALLBACK_PROVIDER=groq       # Fallback

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral

# Groq
GROQ_API_KEY=your_groq_key

# Gemini
GEMINI_API_KEY=your_gemini_key
```

## Service Features

✅ Multi-provider LLM support (Ollama, Groq, Gemini)
✅ Automatic fallback when primary fails
✅ PostgreSQL database storage
✅ Mood history tracking
✅ Error handling and logging
✅ Input validation
✅ Automatic database initialization

## Mood Categories Recognized

The system can detect and classify moods including:
- Happy, Sad, Angry, Anxious, Neutral, Excited, Calm, Confused, Stressed, Overwhelmed, etc.

## Testing

```bash
# Run tests
pytest tests/test_mood_analyzer.py -v

# Run specific test
pytest tests/test_mood_analyzer.py::test_parse_llm_response_valid_json -v

# Run with coverage
pytest tests/ --cov=app
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `psycopg2.OperationalError` | PostgreSQL not running or wrong credentials |
| `Connection refused` to Ollama | Run `ollama serve` |
| `401 Unauthorized` | Check API keys in .env |
| `JSON decode error` | LLM not returning valid JSON |

## LLM Provider Comparison

| Provider | Setup | Speed | Cost | Quality |
|----------|-------|-------|------|---------|
| Ollama | Local/Free | Medium | Free | Good |
| Groq | API Key | Fast | Paid | Excellent |
| Gemini | API Key | Medium | Paid | Excellent |

## Common Commands

```bash
# Start application
python app/main.py

# Test PostgreSQL connection
psql postgresql://user:password@localhost:5432/wellbeing_coach

# Test Ollama
curl http://localhost:11434/api/tags

# View API docs
# Open browser to http://localhost:8000/docs

# Run tests
pytest tests/ -v

# Install dev dependencies
pip install -r requirements.txt
```

## File Descriptions

### Core Service (`app/service/mood_analyser.py`)
Main service class `MoodAnalyzerService` that:
1. Takes user_id and text
2. Tries primary LLM provider
3. Falls back to secondary provider if fails
4. Returns default response if both fail
5. Stores result in database
6. Retrieves mood history

### Database Models (`app/database/models.py`)
`MoodAnalysis` ORM model with fields:
- user_id, input_text, mood_analysed, reason_for_mood
- confidence_score, llm_provider
- created_at, updated_at timestamps

### LLM Config (`app/llm/config.py`)
Configuration classes for:
- Ollama (local endpoint, model name)
- Groq (API key, model name)
- Gemini (API key, model name)

---

**Need more details? See SETUP.md or IMPLEMENTATION_SUMMARY.md**
