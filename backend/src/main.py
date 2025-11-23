from contextlib import asynccontextmanager

import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.database import check_database_connection, create_tables
from src.core import logger
from src.models.paper import Paper
from src.models.user import User, UserPreferences
from src.services.knowledge_graph.neo4j_client import close_shared_driver
from src.routes.assistant import router as assistant_router
from src.routes.search import router as search_router
from src.routes.chat import router as chat_router
from src.routes.auth import router as auth_router
from src.routes.preferences import router as preferences_router
from src.routes.history import router as history_router
from src.routes.graph import router as graph_router
from src.routes.recommendations import router as recommendations_router
from src.routes.interactions import router as interactions_router

settings = get_settings()


class JSONResponseWithJson(JSONResponse):
    def json(self):
        return json.loads(self.body.decode(self.charset))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for application startup and shutdown."""
    
    logger.info("Starting ResearchMind application")
    
    try:
        if await check_database_connection():
            logger.info("Database connection established")
            await create_tables()
            logger.info("Database tables created successfully!")
        else:
            logger.error("Database connection failed")
            raise RuntimeError("Failed to connect to database")
        
        logger.info("ResearchMind application started")
        yield

        try:
            close_shared_driver()
        except Exception as e:
            logger.error(f"Error while closing Neo4j driver during shutdown: {e}")

    except Exception as e:
        logger.error(f"Failed to start ResearchMind application: {e}")
        raise

app = FastAPI(
    title=settings.app_name,
    description="ResearchMind is a research assistant that helps you find relevant papers and insights.",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.185:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(preferences_router)
app.include_router(assistant_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(history_router)
app.include_router(graph_router)
app.include_router(recommendations_router)
app.include_router(interactions_router)

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponseWithJson(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service status."""
    services = {}
    try:
        if await check_database_connection():
            services["postgresql"] = "healthy"
        else:
            services["postgresql"] = "unhealthy"
    except Exception:
        services["postgresql"] = "unhealthy"
    
    all_healthy = all(status == "healthy" for status in services.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": settings.app_version,
        "services": services
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to ResearchMind API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/test/database")
async def test_database():
    """Test PostgreSQL connection."""
    try:
        if await check_database_connection():
            return {"status": "success", "message": "Database connection successful"}
        else:
            raise HTTPException(status_code=500, detail="Database connection failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
