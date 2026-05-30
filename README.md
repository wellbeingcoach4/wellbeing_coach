# Wellbeing Coach

Wellbeing Coach is an AI-powered backend service that helps users improve their emotional wellbeing in short, actionable sessions. It analyzes free-text mood input using configurable large language models (LLMs), generates personalized wellbeing activities (meditation, breathing, journaling, and more), captures user feedback to refine future recommendations, and surfaces historical mood trends with AI-generated insights.

The application is built as a modular FastAPI REST API backed by PostgreSQL. It follows a layered architecture—routes, services, repositories, and schemas—with provider-agnostic LLM integration and automatic fallback when a primary AI provider is unavailable. The design goal is to deliver meaningful wellbeing support within approximately five minutes, aligned with the project's functional requirements.

Target users include individuals seeking quick mood support, client applications integrating wellbeing features, and developers extending the platform with new activities or analytics.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Database](#database)
- [Logging](#logging)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Deployment](#deployment)
- [Monitoring & Observability](#monitoring--observability)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Future Enhancements](#future-enhancements)


---

# Overview

## Purpose

Wellbeing Coach provides a backend API for mood detection, personalized wellbeing session generation, feedback collection, and longitudinal mood analytics. It combines structured data persistence with AI-driven personalization to help users understand and improve their emotional state.

## Problem It Solves

Many wellbeing tools require long onboarding or generic content. This service addresses that by:

- Detecting mood and context from natural language input
- Generating tailored, time-bounded session plans based on mood and past feedback
- Learning from user ratings and feedback text to improve future recommendations
- Summarizing mood patterns over configurable date ranges

## Target Users

- **End users** interacting through a client app (web or mobile) that calls these APIs
- **Developers** building wellbeing or mental-health companion features
- **Product teams** demonstrating a working prototype for quick wellbeing interventions

## Key Business Objective

Help users feel better in approximately five minutes by delivering personalized, AI-generated wellbeing activities informed by their current mood, available time, and historical feedback.

---

# Features

## User Features

- **Mood analysis** — Submit free-text descriptions and receive detected mood, reason, confidence score, and LLM provider metadata
- **Activity catalog** — Browse predefined wellbeing activities (Meditation, Breathing Exercise, Journaling, Stretching, Focus Session)
- **Personalized sessions** — Select an activity (or provide a custom one) and receive an AI-generated session plan with title, steps, duration, and mood context
- **Feedback submission** — Rate and describe session experiences to improve future recommendations
- **Complete history** — Retrieve all mood analyses, feedback entries, and activity selections for a user
- **Periodic mood insights** — Analyze mood trends over a date range with statistics, AI period analysis, and recommendations

## System Features

- **Multi-provider LLM integration** — Ollama (local), Groq, and Google Gemini with configurable primary/fallback routing
- **Provider fallback** — Automatic retry with a secondary provider; safe default responses when all providers fail
- **Centralized logging** — Console and rotating file output with request/response middleware
- **Health check endpoint** — Service readiness probe at `/health`
- **Interactive API docs** — Swagger UI at `/docs` and ReDoc at `/redoc`
- **Schema validation** — Pydantic models with custom validators (e.g., malformed JSON → HTTP 400)
- **Automated testing** — 119 unit and integration tests with ~98% code coverage

---

# Tech Stack

| Category         | Technology                                      |
| ---------------- | ----------------------------------------------- |
| Language         | Python 3.12+                                    |
| Framework        | FastAPI 0.136+                                  |
| ASGI Server      | Uvicorn 0.48+                                   |
| Database         | PostgreSQL (runtime); SQLite in-memory (tests)  |
| ORM              | SQLAlchemy 2.0+                                 |
| DB Driver        | psycopg2 2.9+                                   |
| HTTP Client      | httpx (LLM API calls)                           |
| Validation       | Pydantic (via FastAPI)                          |
| Config           | python-dotenv                                   |
| Monitoring       | Application logging + `/health` endpoint        |
| Testing          | pytest 9.0+, pytest-cov 7.1+                    |
| Linting          | pylint 4.0+ (declared in root `pyproject.toml`) |

> **Note:** LLM calls are made directly via `httpx` to OpenAI-compatible endpoints.

---

# Architecture

## High-Level Architecture

The application follows a **layered (n-tier) architecture** with clear separation of concerns:

| Layer        | Responsibility                                              |
| ------------ | ----------------------------------------------------------- |
| Routes       | HTTP handling, request validation, error mapping            |
| Services     | Business logic, LLM orchestration, fallback handling          |
| Repository   | Database CRUD and query operations                          |
| Models       | SQLAlchemy ORM table definitions                            |
| Schemas      | Pydantic request/response contracts                         |
| LLM Config   | Environment-driven provider and model configuration         |

## Design Patterns

- **Dependency Injection** — FastAPI `Depends(get_db)` injects database sessions per request
- **Repository Pattern** — All persistence logic centralized in `app/database/repository.py`
- **Service Layer Pattern** — Business logic isolated from HTTP and database details
- **Strategy / Fallback Pattern** — Primary LLM provider with configurable fallback and default responses
- **Lifecycle Management** — FastAPI `lifespan` context manager for DB init/shutdown

## Request Flow

```
Client
  │
  ▼
FastAPI Route (validation via Pydantic schema)
  │
  ▼
Service Layer (LLM call → validate → persist)
  │
  ├──► LLM Provider (Ollama / Groq / Gemini)
  │
  ▼
Repository Layer
  │
  ▼
PostgreSQL
  │
  ▼
JSON Response to Client
```

## Data Flow (Mood Analysis Example)

```
POST /mood/analyze_mood
  → MoodAnalyzerService.analyze_mood()
    → Try primary LLM provider
    → On failure, try fallback provider
    → Validate JSON response
    → repository.save_mood_analysis()
  → MoodResponse (mood, reason, confidence, provider, database_id)
```

## ASCII Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Applications                      │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/JSON
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │  /mood   │ │/wellbeing│ │/feedback │ │ /user/...     │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬────────┘  │
│       │            │            │               │           │
│  ┌────▼────────────▼────────────▼───────────────▼────────┐  │
│  │              Service Layer                             │  │
│  │  MoodAnalyzer │ Wellbeing │ Feedback │ UserHistory   │  │
│  └────┬──────────┬───────────┬───────────┬───────────────┘  │
│       │          │           │           │                   │
│  ┌────▼──────────▼───────────▼───────────▼───────────────┐  │
│  │              Repository Layer                          │  │
│  └────────────────────────┬───────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼───────────────────────────────┐  │
│  │         LLM Config (Primary + Fallback)               │  │
│  │    Ollama  ◄──►  Groq  ◄──►  Gemini                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Logging (stdout + app/logs/app.log)                  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    └─────────────────┘
```

Additional diagrams are available in [`app/architecture_diagram.md`](app/architecture_diagram.md) and [`app/flow_diagram.md`](app/flow_diagram.md).

---

# Project Structure

```
wellbeing_coach/
├── app/
│   ├── main.py                      # FastAPI app entry, middleware, lifespan
│   ├── core/
│   │   └── logger.py                # Centralized logging configuration
│   ├── database/
│   │   ├── connection.py            # Engine, session factory, init_db/close_db
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── repository.py            # Data access layer
│   │   └── wellbeing_queries.py     # Static activity catalog
│   ├── llm/
│   │   └── config.py                # LLM provider configuration
│   ├── route/
│   │   ├── mood_analysis_routes.py  # Mood analysis endpoints
│   │   ├── wellbeing_routes.py      # Activity catalog & session generation
│   │   ├── feedback_routes.py       # Feedback submission
│   │   └── user_history_routes.py   # History & periodic mood APIs
│   ├── schema/
│   │   ├── mood_schema.py
│   │   ├── wellbeing_schema.py
│   │   ├── feedback_schema.py
│   │   └── user_history_schema.py
│   ├── service/
│   │   ├── mood_analyser.py         # Mood analysis + LLM calls
│   │   ├── wellbeing_service.py     # Session generation + LLM calls
│   │   ├── feedback_service.py      # Feedback persistence logic
│   │   └── user_history_service.py  # History aggregation + periodic analysis
│   ├── logs/                        # Rotating log files (gitignored *.log)
│   ├── architecture_diagram.md
│   ├── flow_diagram.md
│   └── README.md                    # Supplementary app-level documentation
├── tests/
│   ├── integration/                 # API integration tests (TestClient)
│   └── unit/                        # Service, repository, and config unit tests
├── pyproject.toml                   # Root project dependencies
├── uv.lock                          # uv lockfile
├── .python-version                  # Python 3.12
├── functional_requirements.txt      # Project requirements brief
└── README.md                        # This file
```

| Folder / File       | Responsibility                                              |
| ------------------- | ----------------------------------------------------------- |
| `app/route/`        | HTTP endpoints, status code mapping, route-level logging    |
| `app/service/`      | Core business logic and LLM orchestration                   |
| `app/database/`     | Connection management, ORM models, repository queries       |
| `app/schema/`       | Pydantic request/response validation models                 |
| `app/llm/`          | Provider enum, env-driven configuration                   |
| `app/core/`         | Cross-cutting concerns (logging)                            |
| `tests/integration/`| End-to-end API tests with mocked LLM HTTP clients          |
| `tests/unit/`       | Isolated tests for services, repository, and config         |

---

# Prerequisites

| Requirement        | Version / Details                                      |
| ------------------ | ------------------------------------------------------ |
| Python             | 3.12+ (see `.python-version`)                        |
| PostgreSQL         | Required for local/runtime (default port 5432)         |
| LLM Provider       | At least one of: Ollama (local), Groq, or Gemini       |

**Recommended for local development:**

- Ollama running locally at `http://localhost:11434` with model `llama3.1:8b` (default)
- PostgreSQL database named `wellbeing_coach`

---

# Installation

## Clone Repository

```bash
git clone https://github.com/wellbeingcoach4/wellbeing_coach.git
cd wellbeing_coach
```

## Create Virtual Environment

**Linux / macOS:**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## Install Dependencies

```bash
pip install -e .
```

**Alternative (uv):**

```bash
uv sync
```

> Install `httpx` explicitly if not pulled in transitively (required by service layer):

```bash
pip install httpx
```

## Configure Environment

Create a `.env` file in the project root (`.env` is gitignored):

```bash
# Linux / macOS — create .env manually using the Configuration section below
```

## Database Setup

1. Start PostgreSQL and create the database:

```sql
CREATE DATABASE wellbeing_coach;
```

2. Set `DATABASE_URL` in your `.env` file (see [Configuration](#configuration)).

3. Tables are created automatically on application startup via `init_db()` → `Base.metadata.create_all()`.

## Verify Installation

```bash
# Run the test suite
pytest -v

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Check health
curl http://localhost:8000/health
```

Expected health response:

```json
{"status": "ok", "service": "wellbeing-coach"}
```

---

# Configuration

Environment variables are loaded via `python-dotenv` in `app/llm/config.py`. Database settings are read directly from `os.getenv` in `app/database/connection.py`.

| Variable               | Required | Default                                                                 | Description |
| ---------------------- | -------- | ----------------------------------------------------------------------- | ----------- |
| `DATABASE_URL`         | No       | `postgresql://postgres:passShubhi@localhost:5432/wellbeing_coach`     | PostgreSQL connection string |
| `SQL_ECHO`             | No       | `False`                                                                 | Enable SQLAlchemy SQL query logging (`true`/`false`) |
| `LLM_PROVIDER`         | No       | `ollama`                                                                | Primary LLM provider: `ollama`, `groq`, or `gemini` |
| `LLM_FALLBACK_PROVIDER`| No       | `groq`                                                                  | Fallback LLM provider when primary fails |
| `LOCAL_BASE_URL`       | No       | `http://localhost:11434`                                                | Ollama API base URL |
| `LOCAL_MODEL`          | No       | `llama3.1:8b`                                                           | Ollama model name |
| `OLLAMA_TIMEOUT`       | No       | `180`                                                                   | Ollama request timeout (seconds) |
| `GROQ_API_KEY`         | Yes*     | `""`                                                                    | Groq API key (*required when using Groq) |
| `GROQ_BASE_URL`        | No       | `https://api.groq.com/openai/v1`                                        | Groq API base URL |
| `GROQ_MODEL`           | No       | `llama-3.1-8b-instant`                                                  | Groq model name |
| `GROQ_TIMEOUT`         | No       | `30`                                                                    | Groq request timeout (seconds) |
| `GEMINI_API_KEY`       | Yes*     | `""`                                                                    | Gemini API key (*required when using Gemini) |
| `GEMINI_BASE_URL`      | No       | `https://generativelanguage.googleapis.com/v1beta/openai`               | Gemini OpenAI-compatible base URL |
| `GEMINI_MODEL`         | No       | `gemini-2.5-flash`                                                      | Gemini model name |
| `GEMINI_TIMEOUT`       | No       | `30`                                                                    | Gemini request timeout (seconds) |
| `LOG_LEVEL`            | No       | `INFO`                                                                  | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

**Alternate environment variable names supported:**

- `GROQ_APIKEY` (alias for `GROQ_API_KEY`)
- `GROQ_MODEL_NAME` (alias for `GROQ_MODEL`)

> **Note:**  Use the table above to create your `.env` manually.

### Example `.env`

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/wellbeing_coach
SQL_ECHO=false

LLM_PROVIDER=ollama
LLM_FALLBACK_PROVIDER=groq

LOCAL_BASE_URL=http://localhost:11434
LOCAL_MODEL=llama3.1:8b
OLLAMA_TIMEOUT=180

GROQ_API_KEY=
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TIMEOUT=30

GEMINI_API_KEY=
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT=30

LOG_LEVEL=INFO
```

---

# Running the Application

## Local Development

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or run as a module (enables auto-reload):

```bash
python -m app.main
```

**Service URLs:**

| URL                              | Description          |
| -------------------------------- | -------------------- |
| `http://localhost:8000`          | Root (redirects to `/docs`) |
| `http://localhost:8000/docs`     | Swagger UI           |
| `http://localhost:8000/redoc`    | ReDoc                |
| `http://localhost:8000/health`   | Health check         |


## Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Debug Mode

Enable verbose logging:

```env
LOG_LEVEL=DEBUG
SQL_ECHO=true
```

Restart the application after changing environment variables.

---

# API Documentation

All endpoints are unauthenticated. Interactive documentation is available at `/docs` (Swagger UI) and `/redoc`.

## System APIs

### GET /health

Service health check.

**Authentication:** None

**Response Example:**

```json
{
  "status": "ok",
  "service": "wellbeing-coach"
}
```

### GET /

Redirects to `/docs`. Not included in OpenAPI schema.

---

## Mood APIs

### POST /mood/analyze_mood

Analyze mood from user-provided text using LLM providers with fallback.

**Authentication:** None

**Request Example:**

```json
{
  "user_id": "user01",
  "text": "I feel overwhelmed with work today."
}
```

| Field     | Type   | Constraints                                      |
| --------- | ------ | ------------------------------------------------ |
| `user_id` | string | 1–6 chars, alphanumeric with `-` or `_`          |
| `text`    | string | 1–1000 chars                                     |

**Response Example:**

```json
{
  "mood_analysed": "anxious",
  "reason_for_mood": "The text indicates feelings of overwhelm related to work.",
  "confidence_score": 0.9,
  "llm_provider": "groq",
  "database_id": 12
}
```

**Error Responses:**

- `400` — Malformed JSON in request body
- `422` — Schema validation failure (e.g., empty `user_id`)

---

## Wellbeing APIs

### GET /wellbeing/activities

Returns the static catalog of predefined wellbeing activities.

**Authentication:** None

**Response Example:**

```json
{
  "activities": [
    {
      "activity_id": 1,
      "activity_name": "Meditation",
      "description": "Guided mindfulness and relaxation"
    },
    {
      "activity_id": 2,
      "activity_name": "Breathing Exercise",
      "description": "Deep breathing for stress reduction"
    }
  ]
}
```

**Available activities:** Meditation (1), Breathing Exercise (2), Journaling (3), Stretching (4), Focus Session (5).

### POST /wellbeing/select-activity

Generate a personalized AI wellbeing session based on activity selection, mood, and past feedback.

**Authentication:** None

**Request Example:**

```json
{
  "user_id": "user01",
  "activity_id": 1,
  "available_time_minutes": 10,
  "mood": "stressed",
  "user_reason_for_mood": "Busy workday"
}
```

| Field                    | Type    | Required | Description |
| ------------------------ | ------- | -------- | ----------- |
| `user_id`                | string  | Yes      | Alphanumeric with `-` or `_` |
| `activity_id`            | integer | Yes      | 1–5 for predefined; use `0` with `custom_activity` |
| `available_time_minutes` | integer | No       | Available time for the session |
| `mood`                   | string  | No       | Current mood context |
| `user_reason_for_mood`   | string  | No       | Max 500 chars; double quotes escaped for LLM safety |
| `custom_activity`        | string  | No       | 3–255 chars; required when `activity_id` is `0` |

**Custom activity example:**

```json
{
  "user_id": "user01",
  "activity_id": 0,
  "available_time_minutes": 20,
  "custom_activity": "Morning yoga flow",
  "mood": "anxious"
}
```

**Response Example:**

```json
{
  "message": "Session generated successfully",
  "activity_name": "Meditation",
  "available_time_minutes": 10,
  "session_plan": {
    "session_title": "Calm Breathing",
    "session_steps": ["Inhale deeply", "Hold for 4 seconds", "Exhale slowly"],
    "estimated_duration": "10 minutes",
    "provider_used": "ollama",
    "mood_addressed": "Stress relief through guided breathing"
  },
  "database_id": 7
}
```

**Error Responses:**

- `400` — Invalid `activity_id` or missing `custom_activity` when `activity_id` is `0`
- `422` — Schema validation failure

---

## Feedback APIs

### POST /feedback/

Submit user feedback for a completed wellbeing session.

**Authentication:** None

**Request Example:**

```json
{
  "user_id": "user01",
  "feedback_text": "Very helpful session",
  "rating": 5,
  "activity_selection": "Meditation",
  "user_activity_selection_id": 7
}
```

| Field                        | Type    | Required | Description |
| ---------------------------- | ------- | -------- | ----------- |
| `user_id`                    | string  | Yes      | Min length 1 |
| `feedback_text`              | string  | Yes      | Min length 1 |
| `rating`                     | integer | No       | 1–5 scale |
| `activity_selection`         | string  | Yes      | Activity name, max 255 chars |
| `user_activity_selection_id` | integer | Yes      | Must match an existing session for the user |

**Response Example:**

```json
{
  "message": "Feedback saved successfully",
  "database_id": 3,
  "thanks_note": "Thanks for your feedback!"
}
```

**Error Responses:**

- `400` — Invalid `user_activity_selection_id` for the given user
- `500` — Unexpected server error during save

---

## User History APIs

### GET /user/{user_id}/history

Retrieve complete user history: moods, feedback, and activities.

**Authentication:** None

**Path Parameters:**

| Parameter | Type   | Description |
| --------- | ------ | ----------- |
| `user_id` | string | User identifier |

**Response Example:**

```json
{
  "user_id": "user01",
  "mood_history": [
    {
      "id": 1,
      "user_id": "user01",
      "mood_analysed": "happy",
      "reason_for_mood": "Positive language detected",
      "confidence_score": 0.85,
      "llm_provider": "ollama",
      "created_at": "2024-01-15T10:30:00",
      "input_text": "I am feeling great today"
    }
  ],
  "feedback_history": [],
  "activity_history": [],
  "total_moods": 1,
  "total_feedback": 0,
  "total_activities": 0
}
```

**Error Responses:**

- `400` — Invalid `user_id`
- `500` — Database query failure

### GET /user/{user_id}/mood/periodic

Analyze mood trends over a date range with statistics and AI-generated insights.

**Authentication:** None

**Query Parameters:**

| Parameter   | Type     | Required | Description |
| ----------- | -------- | -------- | ----------- |
| `from_date` | date/datetime | Yes | Start date (inclusive), e.g. `2024-01-01` or `2024-01-01T00:00:00` |
| `to_date`   | date/datetime | Yes | End date (inclusive), e.g. `2024-01-31` |

**Request Example:**

```bash
curl "http://localhost:8000/user/user01/mood/periodic?from_date=2024-01-01&to_date=2024-01-31"
```

**Response Example:**

```json
{
  "user_id": "user01",
  "from_date": "2024-01-01",
  "to_date": "2024-01-31",
  "llm_provider": "groq",
  "moods_in_period": [
    {
      "id": 1,
      "mood_analysed": "happy",
      "reason_for_mood": "Positive language detected",
      "confidence_score": 0.85,
      "llm_provider": "ollama",
      "created_at": "2024-01-15T10:30:00"
    }
  ],
  "mood_statistics": {
    "total_moods": 15,
    "mood_distribution": {"happy": 7, "calm": 5, "stressed": 3},
    "average_confidence": 0.87,
    "most_common_mood": "happy",
    "least_common_mood": "stressed"
  },
  "period_analysis": "Your overall mood has been positive with occasional stress periods.",
  "recommendation": "Continue engaging in activities that boost happiness and schedule breathing exercises during stressful days."
}
```

**Error Responses:**

- `400` — Invalid `user_id` or `from_date` after `to_date`
- `500` — Database or LLM analysis failure

---

# Database

## Technology

- **Runtime:** PostgreSQL via SQLAlchemy + psycopg2
- **Tests:** SQLite in-memory (`sqlite:///:memory:`)

## Tables

### mood_analysis

| Column             | Type         | Description |
| ------------------ | ------------ | ----------- |
| `id`               | Integer (PK) | Auto-increment primary key |
| `user_id`          | String(255)  | User identifier (indexed) |
| `input_text`       | Text         | Original mood input text |
| `mood_analysed`    | String(100)  | Detected mood label |
| `reason_for_mood`  | Text         | LLM explanation |
| `confidence_score` | Float        | Confidence (0–1), nullable |
| `llm_provider`     | String(50)   | Provider used (`ollama`, `groq`, `gemini`, `default`) |
| `created_at`       | DateTime     | Record creation timestamp |
| `updated_at`       | DateTime     | Last update timestamp |

### user_activity_selection

| Column                   | Type         | Description |
| ------------------------ | ------------ | ----------- |
| `id`                     | Integer (PK) | Auto-increment primary key |
| `user_id`                | String       | User identifier |
| `activity_id`            | Integer      | Activity catalog ID (0 for custom) |
| `activity_name`          | String       | Activity display name |
| `available_time_minutes` | Integer      | User's available time |
| `ai_session_title`       | Text         | AI-generated session title |
| `ai_session_steps`       | JSON         | AI-generated step list |
| `ai_estimated_duration`  | String       | Estimated session duration |
| `llm_provider`           | String       | Provider used for generation |
| `user_reason_for_mood`   | Text         | User's stated mood reason |
| `custom_activity`        | String(255)  | Custom activity name (nullable) |
| `created_at`             | DateTime     | Record creation timestamp |

### user_feedback

| Column                       | Type         | Description |
| ---------------------------- | ------------ | ----------- |
| `id`                         | Integer (PK) | Auto-increment primary key |
| `user_id`                    | String(255)  | User identifier (indexed) |
| `feedback_text`              | Text         | User feedback content |
| `rating`                     | Integer      | Optional 1–5 rating |
| `activity_selection`         | String(255)  | Activity name reviewed |
| `user_activity_selection_id` | Integer (FK) | References `user_activity_selection.id` |
| `created_at`                 | DateTime     | Record creation timestamp |

## Relationships

```
user_activity_selection (1) ──< (N) user_feedback
         ▲
         │ user_activity_selection_id (FK)
         │
    user_feedback
```

`mood_analysis` records are independent per user (no foreign keys to other tables).

## ERD (Textual)

```
┌──────────────────────┐       ┌──────────────────────────┐
│    mood_analysis     │       │  user_activity_selection │
├──────────────────────┤       ├──────────────────────────┤
│ id (PK)              │       │ id (PK)                  │
│ user_id              │       │ user_id                  │
│ input_text           │       │ activity_id              │
│ mood_analysed        │       │ activity_name            │
│ reason_for_mood      │       │ ai_session_title/steps   │
│ confidence_score     │       │ llm_provider             │
│ llm_provider         │       │ created_at               │
│ created_at           │       └────────────┬─────────────┘
└──────────────────────┘                    │ 1
                                            │
                                            │ N
                               ┌────────────▼─────────────┐
                               │     user_feedback        │
                               ├──────────────────────────┤
                               │ id (PK)                  │
                               │ user_id                  │
                               │ feedback_text            │
                               │ rating                   │
                               │ user_activity_selection_id (FK)
                               │ created_at               │
                               └──────────────────────────┘
```

## Migration Process

- **Alembic / migration tooling:** Not found in codebase
- **Current approach:** `Base.metadata.create_all()` on application startup via `init_db()` in the FastAPI lifespan handler
- Tables are created if they do not exist; schema changes require manual intervention

---

# Logging

## Framework

Python standard library `logging` module with centralized configuration in `app/core/logger.py`.

## Log Locations

| Output   | Path / Target              |
| -------- | -------------------------- |
| Console  | stdout                     |
| File     | `app/logs/app.log`         |

## Log Levels

Controlled by the `LOG_LEVEL` environment variable (default: `INFO`). Supported levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`.

## Log Rotation Strategy

`RotatingFileHandler` with:

- **Max file size:** 5 MB (`5 * 1024 * 1024` bytes)
- **Backup count:** 5 rotated files
- **Encoding:** UTF-8

## Log Format

```
%(asctime)s | %(levelname)s | %(name)s | %(funcName)s | %(lineno)d | %(message)s
```

## Sample Log Entries

```
2024-01-15 10:30:00,123 | INFO | app.main | log_requests | 118 | Incoming request method=POST path=/mood/analyze_mood auth_header_present=False
2024-01-15 10:30:01,456 | INFO | app.service.mood_analyser | analyze_mood | 51 | Starting mood analysis workflow
2024-01-15 10:30:02,789 | INFO | app.main | log_requests | 132 | Request completed method=POST path=/mood/analyze_mood status_code=200 duration_ms=1666.00
```

## Additional Logging Behavior

- Request middleware logs method, path, status code, and duration (ms); sensitive payload data is excluded
- Malformed JSON requests are logged at `WARNING` level
- Uvicorn loggers (`uvicorn`, `uvicorn.error`, `uvicorn.access`) propagate to the root logger for consistent formatting

---

# Testing

## Unit Tests

Located in `tests/unit/`. Cover services, repository, LLM config, and edge cases.

| Test File                          | Coverage Area |
| ---------------------------------- | ------------- |
| `test_mood_analyser_unit.py`       | Mood analysis service, LLM parsing |
| `test_wellbeing_service_unit.py`   | Session generation, validation |
| `test_feedback_service_unit.py`    | Feedback save logic |
| `test_user_history_service_unit.py`| History retrieval, periodic analysis |
| `test_repository_unit.py`          | Database repository functions |
| `test_misc_coverage_unit.py`       | LLM config, logger, connection |
| `test_extra_coverage_unit.py`      | Main lifespan, error paths |

## Integration Tests

Located in `tests/integration/`. Use FastAPI `TestClient` with in-memory SQLite and mocked LLM HTTP clients.

| Test File                          | Coverage Area |
| ---------------------------------- | ------------- |
| `test_health_api.py`               | Health endpoint |
| `test_mood_api.py`                 | Mood analysis API |
| `test_wellbeing_api.py`            | Activity catalog and selection |
| `test_feedback_api.py`             | Feedback submission |
| `test_user_history_api.py`         | History and periodic mood APIs |
| `test_mood_errors.py`              | Mood error paths |
| `test_feedback_errors.py`          | Feedback error paths |
| `test_route_error_paths.py`        | Route-level exception handling |
| `test_service_branches_api.py`     | LLM provider branch coverage |

## Coverage

Current coverage (as of last test run):

| Metric            | Value   |
| ----------------- | ------- |
| Total statements  | 1,009   |
| Missed statements | 21      |
| **Coverage**      | **98%** |
| Tests passed      | 119     |

## Commands

```bash
# Run all tests
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Alternative coverage commands
coverage run -m pytest
coverage report
```

**Test configuration notes:**

- Tests set `DATABASE_URL=sqlite:///:memory:` via `conftest.py`
- SQLite engine patch removes unsupported `pool_size`/`max_overflow` kwargs
- LLM HTTP clients (`httpx.AsyncClient`) are mocked for deterministic responses

---

# Code Quality

## Linting

**pylint** is declared as a dependency in root `pyproject.toml`:

```bash
pylint app/
```

# Deployment

## Deployment Process

No automated deployment pipeline or container manifests exist in the repository. Deploy manually using the steps below.

## Environment Setup

1. Provision PostgreSQL and set `DATABASE_URL`
2. Configure LLM provider credentials (`GROQ_API_KEY`, `GEMINI_API_KEY`, or local Ollama)
3. Set `LOG_LEVEL` appropriately for the environment
4. Ensure `app/logs/` directory is writable for file logging

## Build Process

No build step required. Install dependencies and run:

```bash
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
---

# Monitoring & Observability

| Capability        | Implementation                                              | Status |
| ----------------- | ----------------------------------------------------------- | ------ |
| Health checks     | `GET /health` returns `{"status": "ok", "service": "wellbeing-coach"}` | Implemented |
| Request logging   | HTTP middleware logs method, path, status, duration         | Implemented |
| File logging      | Rotating logs at `app/logs/app.log`                         | Implemented |

The middleware logs whether an `Authorization` header is present but does not enforce authentication.

---


## Secrets Management

- API keys (`GROQ_API_KEY`, `GEMINI_API_KEY`) and database credentials are loaded from environment variables via `python-dotenv`
- `.env` files are gitignored

## Secure Configuration Recommendations

- Never commit `.env` files or expose API keys in source code
- Override the default `DATABASE_URL` in production
- Add authentication (API keys, JWT, OAuth) before exposing to the public internet
- Run behind HTTPS via a reverse proxy
- Restrict PostgreSQL network access to the application host

---

# Troubleshooting

| Problem | Cause | Solution |
| ------- | ----- | -------- |
| Application fails on startup with DB error | PostgreSQL not running or invalid `DATABASE_URL` | Verify PostgreSQL is running; set correct `DATABASE_URL` in `.env` |
| LLM returns `default` provider with neutral mood | Both primary and fallback providers failed | Check provider availability, API keys, model names, and network connectivity |
| Groq/Gemini returns 401 | Missing or invalid API key | Set `GROQ_API_KEY` or `GEMINI_API_KEY` in `.env` |
| Ollama connection refused | Ollama service not running | Start Ollama locally; verify `LOCAL_BASE_URL` (default `http://localhost:11434`) |
| HTTP 422 on mood analysis | Invalid request body | Ensure `user_id` is 1–6 alphanumeric chars; `text` is 1–1000 chars |
| HTTP 400 malformed JSON | Invalid JSON syntax in request body | Fix JSON formatting; escape double quotes inside strings as `\"` |
| HTTP 400 on select-activity | Invalid `activity_id` or missing `custom_activity` | Use IDs 1–5, or `activity_id: 0` with `custom_activity` |
| HTTP 400 on feedback | `user_activity_selection_id` doesn't belong to user | Submit feedback referencing a valid session ID from a prior `/wellbeing/select-activity` call |
| Empty periodic mood analysis | No mood records in date range | Ensure moods exist for the user within `from_date`–`to_date` |
| Logs not written to file | `app/logs/` not writable | Ensure directory exists and process has write permissions |
| Tests fail with import errors | Missing dependencies or wrong Python version | Use Python 3.12+; run `pip install -e .` and `pip install httpx` |

---

# Contributing

1. Fork the repository at [https://github.com/wellbeingcoach4/wellbeing_coach](https://github.com/wellbeingcoach4/wellbeing_coach)
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make changes following the existing module boundaries: `route → service → repository`
4. Add or update tests for behavior changes
5. Run the test suite:

```bash
pytest -v
pytest --cov=app --cov-report=term-missing
```

6. Keep API contracts synchronized with Pydantic schema models
7. Document new environment variables and endpoints in this README
8. Create a pull request with a clear description of changes

---

# Future Enhancements

Based on architecture analysis and existing documentation references:

- **Database migrations** — Add Alembic instead of startup-only `create_all()` for safe schema evolution
- **Authentication & authorization** — Protect endpoints and enforce user-scoped data access
- **Pagination & filtering** — Add to history endpoints for large datasets

---
