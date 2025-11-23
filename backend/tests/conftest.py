import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base
from src.models.user import User
from src.models.paper import Paper


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing."""
    from src.config import Settings
    
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="test_password",
        qdrant_host="localhost",
        qdrant_port=6333,
        openai_api_key="test_key",
        jwt_secret_key="test_secret_key_for_testing_only",
        debug=True,
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def async_engine(test_settings):
    """Create async test database engine."""
    engine = create_async_engine(
        test_settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async test database session."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def sync_engine(test_settings):
    """Create sync test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def sync_session(sync_engine) -> Generator[Session, None, None]:
    """Create sync test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
    session = SessionLocal()
    
    yield session
    
    session.rollback()
    session.close()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "hashed_password": "hashed_password_here",
        "full_name": "Test User",
        "is_active": True,
        "is_verified": True,
    }


@pytest.fixture
def sample_paper_data():
    """Sample paper data for testing."""
    from datetime import datetime, timezone
    return {
        "arxiv_id": "2301.00001",
        "arxiv_url": "https://arxiv.org/abs/2301.00001",
        "pdf_url": "https://arxiv.org/pdf/2301.00001.pdf",
        "title": "Test Paper: A Novel Approach",
        "abstract": "This is a test paper abstract.",
        "authors": ["John Doe", "Jane Smith"],
        "published_date": datetime(2023, 1, 1, tzinfo=timezone.utc),
        "primary_category": "cs.AI",
        "categories": ["cs.AI", "cs.LG"],
        "citation_count": 10,
        "is_processed": True,
        "is_embedded": True,
    }


@pytest.fixture
async def test_user(async_session: AsyncSession, sample_user_data) -> User:
    """Create a test user in the database."""
    user = User(**sample_user_data)
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
async def test_paper(async_session: AsyncSession, sample_paper_data) -> Paper:
    """Create a test paper in the database."""
    paper = Paper(**sample_paper_data)
    async_session.add(paper)
    await async_session.commit()
    await async_session.refresh(paper)
    return paper


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content="This is a test response from the AI.")
                )
            ]
        )
    )
    return mock_client


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client."""
    mock_client = AsyncMock()
    mock_client.search = AsyncMock(return_value=[])
    mock_client.upsert = AsyncMock(return_value=True)
    return mock_client


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client."""
    mock_client = MagicMock()
    mock_client.execute_query = MagicMock(return_value=[])
    return mock_client


@pytest.fixture
def mock_embedder():
    """Mock embedding service."""
    mock = MagicMock()
    mock.embed_query.return_value = {
        "dense": [0.1] * 384,
        "sparse": {"indices": [1, 2, 3], "values": [0.5, 0.3, 0.2]}
    }
    mock.embed_documents.return_value = (
        [[0.1] * 384],
        [{"indices": [1, 2, 3], "values": [0.5, 0.3, 0.2]}]
    )
    return mock


@pytest.fixture
def mock_pdf_parser():
    """Mock PDF parser service."""
    mock = AsyncMock()
    mock.parse_pdf.return_value = MagicMock(
        export_to_dict=lambda: {
            "title": "Test Paper",
            "authors": ["Author One"],
            "abstract": "Test abstract",
        }
    )
    return mock


@pytest.fixture
async def test_client():
    """Create test FastAPI client."""
    from httpx import AsyncClient
    from src.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


def create_mock_paper(**overrides):
    """Create a mock paper with default values."""
    defaults = {
        "arxiv_id": "2301.00001",
        "arxiv_url": "https://arxiv.org/abs/2301.00001",
        "pdf_url": "https://arxiv.org/pdf/2301.00001.pdf",
        "title": "Test Paper",
        "abstract": "Test abstract",
        "authors": ["Test Author"],
        "published_date": "2023-01-01T00:00:00Z",
        "primary_category": "cs.AI",
        "categories": ["cs.AI"],
        "citation_count": 0,
    }
    defaults.update(overrides)
    return Paper(**defaults)


def create_mock_user(**overrides):
    """Create a mock user with default values."""
    defaults = {
        "email": "test@example.com",
        "username": "testuser",
        "hashed_password": "hashed",
        "is_active": True,
    }
    defaults.update(overrides)
    return User(**defaults)
