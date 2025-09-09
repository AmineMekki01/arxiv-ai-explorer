from loguru import logger

from contextlib import asynccontextmanager

import redis.asyncio as redis
from qdrant_client import AsyncQdrantClient
from neo4j import AsyncGraphDatabase
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.database import check_database_connection

settings = get_settings()

def _redacted_db_target(dsn: str) -> str:
    """Return a safe string summarizing the DB connection target without secrets."""
    try:
        # Lazy import to avoid adding a hard dependency on sqlalchemy utils here
        from urllib.parse import urlparse
        u = urlparse(dsn)
        # path starts with '/'
        dbname = u.path.lstrip('/') if u.path else ''
        host = u.hostname or ''
        port = u.port or ''
        scheme = u.scheme
        return f"{scheme}://{host}:{port}/{dbname}"
    except Exception:
        return "<unparsed>"

logger.add(
    settings.log_file,
    level=settings.log_level,
    rotation="500 MB",
    retention="30 days",
    backtrace=True,
    diagnose=True,
)

redis_client: redis.Redis = None
qdrant_client: AsyncQdrantClient = None
neo4j_driver = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for application startup and shutdown."""
    
    logger.info("Starting ResearchMind application")
    # Helpful hint for local vs docker DB host misconfigurations
    logger.info(f"Configured DATABASE target: {_redacted_db_target(settings.database_url)}")
    global redis_client, qdrant_client, neo4j_driver

    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        logger.info("Redis connection established")

        qdrant_client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        logger.info("Qdrant connection established")

        neo4j_driver = AsyncGraphDatabase.driver(
            uri=settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        logger.info("Neo4j connection established")
    
        # Wait briefly for Postgres to become ready (useful when starting via Docker)
        db_ok = False
        for attempt in range(1, 6):
            if await check_database_connection():
                db_ok = True
                break
            logger.warning(f"Database not ready yet (attempt {attempt}/5), retrying...")
            await asyncio.sleep(1 * attempt)
        if db_ok:
            logger.info("Database connection established")
        else:
            logger.error("Database connection failed")
        
        logger.info("ResearchMind application started")
    
    except Exception as e:
        logger.error(f"Failed to start ResearchMind application: {e}")
        # Re-raise to let FastAPI fail startup properly
        raise
    
    try:
        yield
    finally:
        logger.info("Closing connections")
        try:
            if redis_client is not None:
                await redis_client.close()
        finally:
            pass
        try:
            if qdrant_client is not None:
                await qdrant_client.close()
        finally:
            pass
        try:
            if neo4j_driver is not None:
                await neo4j_driver.close()
        finally:
            pass
        logger.info("ResearchMind application stopped")

app = FastAPI(
    title=settings.app_name,
    description="ResearchMind is a research assistant that helps you find relevant papers and insights.",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
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
        await redis_client.ping()
        services["redis"] = "healthy"
    except Exception:
        services["redis"] = "unhealthy"
    
    try:
        await qdrant_client.get_collections()
        services["qdrant"] = "healthy"
    except Exception:
        services["qdrant"] = "unhealthy"
    
    try:
        async with neo4j_driver.session() as session:
            await session.run("RETURN 1")
        services["neo4j"] = "healthy"
    except Exception:
        services["neo4j"] = "unhealthy"
    
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

@app.get("/test/redis")
async def test_redis():
    """Test Redis connection."""
    try:
        await redis_client.set("test_key", "test_value", ex=10)
        value = await redis_client.get("test_key")
        return {"status": "success", "value": value.decode() if value else None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")


@app.get("/test/qdrant")
async def test_qdrant():
    """Test Qdrant connection."""
    try:
        collections = await qdrant_client.get_collections()
        return {"status": "success", "collections": [c.name for c in collections.collections]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qdrant error: {str(e)}")


@app.get("/test/neo4j")
async def test_neo4j():
    """Test Neo4j connection."""
    try:
        async with neo4j_driver.session() as session:
            result = await session.run("RETURN 'Connection successful' as message")
            record = await result.single()
            return {"status": "success", "message": record["message"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j error: {str(e)}")


@app.get("/test/database")
async def test_database():
    """Test PostgreSQL connection."""
    try:
        if await check_database_connection():
            return {"status": "success", "message": "Database connection successful"}
        else:
            raise HTTPException(status_code=500, detail="Database connection failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
