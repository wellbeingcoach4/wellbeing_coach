"""
Main FastAPI application for Wellbeing Coach
"""
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.database import init_db, close_db
from app.route.mood_analysis_routes import router as mood_router
from fastapi import FastAPI
from app.route.wellbeing_routes import router as wellbeing_router
from app.route.feedback_routes import router as feedback_router
from app.route.user_history_routes import router as user_history_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle (startup and shutdown)
    """
    # Startup
    logger.info("Initializing database...")
    init_db()
    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Closing database connections...")
    close_db()
    logger.info("Application shutdown complete")


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
