from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from src.config import get_settings

_async_engine = None
_sync_engine = None
_AsyncSessionLocal = None
_SessionLocal = None

def _get_engines():
    """Lazy initialization of database engines."""
    global _async_engine, _sync_engine, _AsyncSessionLocal, _SessionLocal
    
    if _async_engine is None:
        settings = get_settings()
        
        if not settings.database_url:
            return None, None, None, None
            
        async_database_url = settings.database_url.replace("postgresql", "postgresql+asyncpg")
        
        _async_engine = create_async_engine(
            async_database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        
        _sync_engine = create_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        
        _AsyncSessionLocal = sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        _SessionLocal = sessionmaker(
            bind=_sync_engine,
            class_=Session,
            expire_on_commit=False,
        )
    
    return _async_engine, _sync_engine, _AsyncSessionLocal, _SessionLocal

Base = declarative_base()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async session for database operations."""
    _, _, AsyncSessionLocal, _ = _get_engines()
    
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not configured - missing DATABASE_URL")
        
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Get a sync session for database operations."""
    _, _, _, SessionLocal = _get_engines()
    
    if SessionLocal is None:
        raise RuntimeError("Database not configured - missing DATABASE_URL")
        
    with SessionLocal() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

def provide_sync_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a sync Session.
    Wraps get_sync_session() context manager for use with Depends().
    """
    with get_sync_session() as session:
        yield session

async def check_database_connection() -> bool:
    """Check if the database connection is working."""
    try:
        _, _, AsyncSessionLocal, _ = _get_engines()
        if AsyncSessionLocal is None:
            return False
            
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False

async def create_tables():
    """Create all tables if not created and modify if needed"""
    async_engine, _, _, _ = _get_engines()
    
    if async_engine is None:
        raise RuntimeError("Database not configured - missing DATABASE_URL")
        
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)       
