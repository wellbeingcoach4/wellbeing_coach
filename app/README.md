# Wellbeing Coach

AI-powered FastAPI backend for mood analysis, personalized wellbeing session generation, user feedback capture, and historical mood trend insights.

## Project Overview

Wellbeing Coach exposes REST APIs that:
- analyze user mood from free text using configurable LLM providers (with fallback),
- generate personalized wellbeing session plans from activity selection + mood context,
- store user feedback and activity history,
- provide user history and periodic mood analysis summaries.

The project follows a modular backend architecture with route, service, repository, schema, and database layers.

## Features

- Multi-provider LLM integration: `ollama`, `groq`, `gemini`
- Provider fallback strategy for resilience
- Structured mood analysis responses with confidence and provider metadata
- Personalized session generation using recent feedback context
- User history aggregation (moods, feedback, activities)
- Periodic mood analytics (distribution, confidence average, AI summary/recommendation)
- Centralized logging with rotating file handler
- Automated tests (unit + integration) with SQLite-backed test setup

## Tech Stack

- **Language:** Python 3.12+
- **API Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **ORM/DB Layer:** SQLAlchemy
- **Primary Database (runtime):** PostgreSQL (`psycopg2`)
- **HTTP Client for LLM calls:** `httpx`
- **Config Handling:** `python-dotenv`
- **Validation/Schemas:** Pydantic
- **Testing:** `pytest`, `pytest-cov`

## Architecture Overview

- **Routes (`app/route`)**: HTTP request/response handling and endpoint-level validation/error mapping.
- **Services (`app/service`)**: Core business logic (mood analysis, wellbeing generation, feedback flow, periodic analysis).
- **Repository (`app/database/repository.py`)**: Database persistence and query functions.
- **Schemas (`app/schema`)**: Pydantic contracts for request/response models.
- **LLM Config (`app/llm/config.py`)**: Provider selection, fallback selection, env-driven model/base URL/API key config.
- **App Entry (`app/main.py`)**: FastAPI app setup, startup/shutdown lifecycle, middleware, exception handlers.

## Folder Structure

```text
.
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── logger.py
│   │   └── generate_readme.py
│   ├── database/
│   │   ├── connection.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── wellbeing_queries.py
│   ├── llm/
│   │   └── config.py
│   ├── route/
│   │   ├── mood_analysis_routes.py
│   │   ├── wellbeing_routes.py
│   │   ├── feedback_routes.py
│   │   └── user_history_routes.py
│   ├── schema/
│   │   ├── mood_schema.py
│   │   ├── wellbeing_schema.py
│   │   ├── feedback_schema.py
│   │   └── user_history_schema.py
│   └── service/
│       ├── mood_analyser.py
│       ├── wellbeing_service.py
│       ├── feedback_service.py
│       └── user_history_service.py
├── tests/
│   ├── integration/
│   └── unit/
├── API_DOCUMENTATION.md
├── SETUP.md
├── pyproject.toml
└── uv.lock
```

## Installation Steps

### Prerequisites

- Python `3.12+`
- PostgreSQL (for local runtime)
- At least one LLM provider configured (`ollama` recommended for local-first setup)

### Setup

```bash
# 1) Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 2) Install dependencies
pip install -e .
```

> Alternative: if you use `uv`, install from lockfile/workspace as per your environment conventions.

## Environment Variables Setup

Create `.env` in project root:

```bash
cp .env.example .env  # if you create one from the template below
```

### Suggested `.env.example`

```env
# Database
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/wellbeing_coach
SQL_ECHO=false

# Provider routing
LLM_PROVIDER=ollama
LLM_FALLBACK_PROVIDER=groq

# Ollama (code reads LOCAL_* names)
LOCAL_BASE_URL=http://localhost:11434
LOCAL_MODEL=llama3.1:8b
OLLAMA_TIMEOUT=180

# Groq
GROQ_API_KEY=
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TIMEOUT=30

# Gemini
GEMINI_API_KEY=
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
```

### Notes

- `app/llm/config.py` currently uses `LOCAL_BASE_URL` and `LOCAL_MODEL` for Ollama settings.
- `.env` is ignored by Git (`.gitignore`).

## Running the Application Locally

```bash
# from repo root
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or:

```bash
python -m app.main
```

Service URLs:
- API base: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`

## API Documentation Summary

### Health

- `GET /health` - Service health check

### Mood APIs

- `POST /mood/analyze_mood`
  - Request: `user_id`, `text`
  - Response: `mood_analysed`, `reason_for_mood`, `confidence_score`, `llm_provider`, `database_id`

### Wellbeing APIs

- `GET /wellbeing/activities`
  - Returns static activity catalog from `app/database/wellbeing_queries.py`
- `POST /wellbeing/select-activity`
  - Generates personalized session plan
  - Supports `activity_id = 0` + `custom_activity` for custom activity input

### Feedback APIs

- `POST /feedback/`
  - Stores user feedback and optional rating/activity link

### User History APIs

- `GET /user/{user_id}/history`
  - Aggregates mood, feedback, activity records
- `GET /user/{user_id}/mood/periodic?from_date=...&to_date=...`
  - Date-range mood retrieval + statistics + AI-generated period analysis/recommendation

## Database Setup / Migrations

This project uses SQLAlchemy model metadata creation on startup:
- `init_db()` calls `Base.metadata.create_all(...)`
- No Alembic migration setup is present yet.

### Local DB Quick Start (PostgreSQL)

```sql
CREATE DATABASE wellbeing_coach;
```

Set `DATABASE_URL` accordingly, then start the app. Tables are auto-created from:
- `MoodAnalysis`
- `UserActivitySelection`
- `UserFeedback`

## LLM / AI Integrations

- **Primary/fallback provider selection** is env-driven (`LLM_PROVIDER`, `LLM_FALLBACK_PROVIDER`)
- **Supported providers:** Ollama, Groq, Gemini
- **Pattern used in services:**
  1. Try primary provider
  2. If failure/invalid response, try fallback provider
  3. If both fail, return safe default response

LLMs are used in:
- mood detection (`app/service/mood_analyser.py`)
- wellbeing session generation (`app/service/wellbeing_service.py`)
- periodic mood summary/recommendation (`app/service/user_history_service.py`)

## Logging & Monitoring

- Centralized logger config in `app/core/logger.py`
- Output targets:
  - stdout (console)
  - rotating file: `app/logs/app.log` (5 MB max, 5 backups)
- Request middleware logs method/path/status/duration
- Malformed JSON requests are normalized to HTTP `400` with helpful hints

## Deployment Instructions

No container/orchestration manifests are currently included.

### Minimal production-style run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Recommended production hardening:
- run behind reverse proxy (Nginx/ALB/API Gateway),
- inject secrets via environment manager,
- set `LOG_LEVEL`,
- provide managed PostgreSQL instance,
- add process manager (systemd/supervisor) or container runtime.

## Testing Instructions

Run all tests:

```bash
pytest -v
```

Run with coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

Notes:
- Tests override DB to in-memory SQLite.
- LLM HTTP clients are mocked for deterministic tests.

## Example Requests / Responses

### 1) Analyze Mood

```bash
curl -X POST "http://localhost:8000/mood/analyze_mood" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user01",
    "text": "I feel overwhelmed with work."
  }'
```

```json
{
  "mood_analysed": "anxious",
  "reason_for_mood": "The text indicates overwhelm and stress-related cues.",
  "confidence_score": 0.9,
  "llm_provider": "groq",
  "database_id": 12
}
```

### 2) Get User History

```bash
curl "http://localhost:8000/user/user01/history"
```

### 3) Get Periodic Mood Analysis

```bash
curl "http://localhost:8000/user/user01/mood/periodic?from_date=2024-01-01&to_date=2024-01-31"
```

## Troubleshooting / Common Issues

- **DB connection errors on startup**
  - Verify PostgreSQL is running and `DATABASE_URL` is valid.
- **Provider API errors (`401/429/5xx`)**
  - Validate API keys, model names, and provider base URLs.
- **Ollama unavailable**
  - Start local service and verify `LOCAL_BASE_URL`.
- **422 validation errors**
  - Ensure request body matches schema (required fields, constraints).
- **400 malformed JSON**
  - Fix request JSON syntax (unclosed quotes, invalid escaping, etc.).

## Contributing Guidelines

- Follow project module boundaries (`route -> service -> repository`).
- Add/update tests for behavior changes.
- Keep API contracts synchronized with schema models.
- Document new env vars and endpoints in README/API docs.
- Prefer small, focused pull requests.

## Future Improvements

- Add migration tooling (Alembic) instead of startup `create_all`.
- Add authentication/authorization (currently absent).
- Add pagination/filtering on large history queries.
- Add structured observability (metrics/tracing).
- Add deployment artifacts (Dockerfile, compose, CI/CD pipeline docs).
- Add architecture diagram image once interfaces stabilize.