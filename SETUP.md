# Wellbeing Coach - Mood Analysis Service

## Project Structure

```
app/
├── main.py                    # FastAPI application entry point
├── database/
│   ├── __init__.py           # Database package exports
│   ├── models.py             # SQLAlchemy ORM models
│   └── connection.py         # PostgreSQL connection setup
├── llm/
│   ├── __init__.py           # LLM package exports
│   └── config.py             # LLM configuration and providers
├── route/
│   └── mood_analysis.py      # API endpoints for mood analysis
├── schema/
│   └── mood_schema           # Pydantic request/response schemas
├── service/
│   ├── __init__.py           # Service package exports
│   └── mood_analyser.py      # Mood analysis service logic
└── tests/
```

## Features

### 1. **Multi-Provider LLM Support**
   - **Ollama**: Local LLM (default)
   - **Groq**: Fast cloud-based LLM
   - **Gemini**: Google's Generative AI

### 2. **Fallback Mechanism**
   - Automatically falls back to secondary provider if primary fails
   - Default response if both fail
   - Comprehensive error logging

### 3. **PostgreSQL Database Storage**
   - Persistent mood analysis records
   - Automatic timestamp tracking
   - User mood history retrieval

### 4. **Structured Response Format**
   - `mood_analysed`: Detected mood category
   - `reason_for_mood`: Explanation of the mood detection
   - `confidence_score`: Confidence level (0-1)
   - `llm_provider`: Provider used for analysis
   - `database_id`: Reference to stored record

## Setup Instructions

### Prerequisites
- Python 3.12+
- PostgreSQL database
- One or more LLM providers configured

### 1. Install Dependencies

```bash
# Install required packages
pip install fastapi uvicorn sqlalchemy psycopg2-binary httpx python-dotenv

# Or from pyproject.toml (if configured)
pip install -e .
```

### 2. Database Setup

#### Install PostgreSQL
- Windows: https://www.postgresql.org/download/windows/
- macOS: `brew install postgresql`
- Linux: `apt-get install postgresql`

#### Create Database and User

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE wellbeing_coach;

-- Create user (optional but recommended)
CREATE USER wellbeing_user WITH PASSWORD 'secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE wellbeing_coach TO wellbeing_user;

-- Connect to the database
\c wellbeing_coach

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO wellbeing_user;
```

### 3. Environment Configuration

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your configuration
```

**Example .env file:**
```
DATABASE_URL=postgresql://wellbeing_user:secure_password@localhost:5432/wellbeing_coach
LLM_PROVIDER=ollama
LLM_FALLBACK_PROVIDER=groq
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### 4. LLM Provider Setup

#### Option A: Ollama (Local)
```bash
# Download Ollama from https://ollama.ai
# Run Ollama server
ollama serve

# In another terminal, pull a model
ollama pull mistral
```

#### Option B: Groq (Cloud)
1. Sign up at https://console.groq.com
2. Create an API key
3. Add to .env: `GROQ_API_KEY=your_key`

#### Option C: Gemini (Cloud)
1. Go to https://makersuite.google.com
2. Create an API key
3. Add to .env: `GEMINI_API_KEY=your_key`

### 5. Run the Application

```bash
# Development mode
python app/main.py

# Or with uvicorn directly
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000

## API Documentation

### Health Check
```bash
GET /health
```

### Analyze Mood
```bash
POST /mood/analyze_mood
Content-Type: application/json

{
    "user_id": "user123",
    "text": "I'm feeling really overwhelmed with work and can't seem to find time to relax."
}
```

**Response:**
```json
{
    "mood_analysed": "anxious",
    "reason_for_mood": "The text expresses overwhelming feelings and difficulty managing stress, indicating anxiety.",
    "confidence_score": 0.88,
    "llm_provider": "ollama",
    "database_id": 1
}
```

### Get Mood History
```bash
GET /mood/mood_history/{user_id}?limit=10
```

**Response:**
```json
{
    "user_id": "user123",
    "total_records": 3,
    "records": [
        {
            "id": 3,
            "mood_analysed": "happy",
            "reason_for_mood": "Positive language and excitement about future plans",
            "confidence_score": 0.92,
            "llm_provider": "ollama",
            "created_at": "2024-05-25T10:30:00"
        },
        ...
    ]
}
```

## API Documentation (Auto-generated)
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database Schema

### mood_analysis Table
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

CREATE INDEX idx_user_id ON mood_analysis(user_id);
CREATE INDEX idx_created_at ON mood_analysis(created_at);
```

## Service Architecture

### MoodAnalyzerService
The core service handling mood analysis:

1. **Initialization**: Accepts database session
2. **Primary Analysis**: Attempts with configured primary provider
3. **Fallback Analysis**: Falls back to secondary provider if primary fails
4. **Default Response**: Returns neutral mood if all providers fail
5. **Database Storage**: Persists results for history tracking
6. **History Retrieval**: Fetches user's mood analysis history

### LLM Request Flow
```
Request Text
    ↓
[Try Primary Provider]
    ↓
Success? → Store & Return
    ↓
Failed → [Try Fallback Provider]
    ↓
Success? → Store & Return
    ↓
Failed → [Return Default Response]
    ↓
Store & Return
```

## Configuration Options

### LLM Providers
- `OLLAMA`: Free, runs locally. Requires Ollama server running.
- `GROQ`: Fast, cloud-based. Requires API key.
- `GEMINI`: Google's AI. Requires API key.

### Mood Categories
The system recognizes moods including:
- Happy, Sad, Angry, Anxious, Neutral, Confused, Stressed, Excited, Calm, etc.

## Error Handling

The service includes comprehensive error handling:
1. **LLM Connection Errors**: Automatic fallback to secondary provider
2. **Invalid Responses**: Validates JSON structure, falls back if invalid
3. **Database Errors**: Logs error but doesn't crash, still returns response
4. **API Errors**: Graceful error responses with logging

## Logging

Logs are output to console with timestamps and severity levels:
```
2024-05-25 10:30:15,123 - app.service.mood_analyser - INFO - Starting mood analysis for user: user123
2024-05-25 10:30:16,456 - app.service.mood_analyser - INFO - Mood analysis stored in database with ID: 1
```

## Testing

Example test using curl:
```bash
curl -X POST "http://localhost:8000/mood/analyze_mood" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "text": "I am very happy today!"
  }'
```

## Troubleshooting

### Database Connection Error
```
sqlalchemy.exc.OperationalError: could not connect to server
```
**Solution**: Ensure PostgreSQL is running and credentials in .env are correct.

### Ollama Connection Error
```
Error calling ollama: Connection refused
```
**Solution**: Start Ollama server: `ollama serve`

### Groq/Gemini API Error
```
Error calling groq: 401 Unauthorized
```
**Solution**: Verify API key in .env file

### JSON Parse Error
```
Failed to parse JSON response
```
**Solution**: Ensure LLM is returning valid JSON. Check model configuration.

## Performance Considerations

1. **Timeout Settings**: Each provider has a 30-second timeout
2. **Connection Pooling**: Database uses connection pooling for efficiency
3. **Caching**: Consider adding Redis cache for frequently analyzed texts
4. **Batch Processing**: For large-scale analysis, consider async task queues

## Security Considerations

1. **API Keys**: Never commit .env to version control
2. **Database Credentials**: Use strong passwords
3. **Input Validation**: Text is validated (min 1 character)
4. **User IDs**: Validated for safe characters
5. **Rate Limiting**: Consider adding rate limiting for production

## Future Enhancements

1. Add sentiment analysis alongside mood
2. Implement caching layer (Redis)
3. Add mood trend analysis
4. Support for multiple languages
5. Webhook notifications for mood changes
6. Advanced analytics dashboard
7. User mood patterns and recommendations
8. Integration with wearable devices

## Contributing

1. Follow PEP 8 coding standards
2. Add tests for new features
3. Update documentation
4. Ensure all providers tested before commit

## License

Specify your license here

## Support

For issues and questions, please create an issue in the repository or contact support.
