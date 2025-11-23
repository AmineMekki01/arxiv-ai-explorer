import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.models.paper_interaction import PaperView, PaperLike, PaperSave
from src.models.user import User


@pytest.mark.unit
class TestPaperInteractions:
    """Tests for paper interaction models."""
    
    @pytest.mark.asyncio
    async def test_paper_view_creation(self, async_session):
        """Test creating a paper view."""
        user = User(
            id=uuid4(),
            email="viewer@example.com",
            username="viewer",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        view = PaperView(
            id=uuid4(),
            user_id=str(user.id),
            arxiv_id="2301.00001",
            created_at=datetime.now(timezone.utc)
        )
        
        async_session.add(user)
        async_session.add(view)
        await async_session.commit()
        
        assert view.id is not None
        assert view.user_id == str(user.id)
        assert view.arxiv_id == "2301.00001"
        assert view.created_at is not None
    
    @pytest.mark.asyncio
    async def test_paper_like_creation(self, async_session):
        """Test creating a paper like."""
        user = User(
            id=uuid4(),
            email="liker@example.com",
            username="liker",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        like = PaperLike(
            id=uuid4(),
            user_id=str(user.id),
            arxiv_id="2301.00002",
            created_at=datetime.now(timezone.utc)
        )
        
        async_session.add(user)
        async_session.add(like)
        await async_session.commit()
        
        assert like.id is not None
        assert like.user_id == str(user.id)
        assert like.arxiv_id == "2301.00002"
    
    @pytest.mark.asyncio
    async def test_paper_save_creation(self, async_session):
        """Test creating a paper save."""
        user = User(
            id=uuid4(),
            email="saver@example.com",
            username="saver",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        save = PaperSave(
            id=uuid4(),
            user_id=str(user.id),
            arxiv_id="2301.00003",
            created_at=datetime.now(timezone.utc)
        )
        
        async_session.add(user)
        async_session.add(save)
        await async_session.commit()
        
        assert save.id is not None
        assert save.user_id == str(user.id)
        assert save.arxiv_id == "2301.00003"
    
    @pytest.mark.asyncio
    async def test_multiple_interactions_same_user(self, async_session):
        """Test multiple interactions by same user."""
        user = User(
            id=uuid4(),
            email="active@example.com",
            username="active",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        view = PaperView(
            id=uuid4(),
            user_id=str(user.id),
            arxiv_id="2301.00004",
            created_at=datetime.now(timezone.utc)
        )
        
        like = PaperLike(
            id=uuid4(),
            user_id=str(user.id),
            arxiv_id="2301.00004",
            created_at=datetime.now(timezone.utc)
        )
        
        save = PaperSave(
            id=uuid4(),
            user_id=str(user.id),
            arxiv_id="2301.00004",
            created_at=datetime.now(timezone.utc)
        )
        
        async_session.add(user)
        async_session.add(view)
        async_session.add(like)
        async_session.add(save)
        await async_session.commit()
        
        assert view.arxiv_id == like.arxiv_id == save.arxiv_id
        assert view.user_id == like.user_id == save.user_id
