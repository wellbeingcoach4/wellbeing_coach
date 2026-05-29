"""
Main FastAPI application for Wellbeing Coach
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, RedirectResponse

from app.core.logger import setup_logging
from app.database import init_db, close_db
from app.route.mood_analysis_routes import router as mood_router
from app.route.wellbeing_routes import router as wellbeing_router
from app.route.feedback_routes import router as feedback_router
from app.route.user_history_routes import router as user_history_router

# Configure centralized logging before app startup.
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle (startup and shutdown)
    """
    # Startup
    logger.info("Application startup initiated")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception:
        logger.exception("Database initialization failed during startup")
        raise

    yield

    logger.info("Application shutdown initiated")
    try:
        close_db()
        logger.info("Database connections closed successfully")
    except Exception:
        logger.exception("Database shutdown cleanup failed")
        raise


# Create FastAPI app
app = FastAPI(
    title="Wellbeing Coach",
    description="AI-powered mood analysis and wellbeing support system",
    version="0.1.0",
    lifespan=lifespan
)

# Include routers
app.include_router(mood_router)
app.include_router(wellbeing_router)
app.include_router(feedback_router)
app.include_router(user_history_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    """Translate malformed-JSON errors into a clean 400 response.

    By default FastAPI returns 422 for both schema validation failures
    and unparsable JSON. Here we distinguish the two: a single
    `json_invalid` error indicates the request body was not valid JSON,
    which is a client-side syntax issue best surfaced as 400 with a
    helpful hint. All other validation failures keep the standard 422.
    """
    errors = exc.errors()
    json_errors = [e for e in errors if e.get("type") == "json_invalid"]

    if json_errors:
        first = json_errors[0]
        logger.warning(
            "Malformed JSON in request path=%s msg=%s",
            request.url.path,
            first.get("msg"),
        )
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Malformed JSON in request body",
                "error": first.get("msg"),
                "hint": (
                    "Ensure every string is properly closed and that any "
                    "double quotes inside string values are escaped as \\\""
                ),
            },
        )

    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(errors)},
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log request/response metadata for API observability.

    Sensitive payload data is intentionally excluded.
    """
    start_time = time.perf_counter()
    method = request.method
    path = request.url.path
    has_auth_header = "authorization" in request.headers

    logger.info(
        "Incoming request method=%s path=%s auth_header_present=%s",
        method,
        path,
        has_auth_header,
    )

    try:
        response: Response = await call_next(request)
    except Exception:
        logger.exception("Unhandled exception while processing request path=%s", path)
        raise

    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.info(
        "Request completed method=%s path=%s status_code=%s duration_ms=%.2f",
        method,
        path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/", include_in_schema=False)
async def root():
    """Redirect bare URL to interactive API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "wellbeing-coach"}

# python -m app.main command allows running this file as a module,
# which is important for relative imports to work correctly.
# It tells Python to treat the current directory as a package and run the main.py
# file within that context. This way, all the imports in main.py that reference other
# modules in the app package will work correctly.

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
