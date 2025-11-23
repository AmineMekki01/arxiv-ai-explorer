import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.models.search_history import SearchHistory
from src.models.user import User


@pytest.mark.unit
class TestSearchHistoryModel:
    """Tests for SearchHistory model."""
    
    @pytest.mark.asyncio
    async def test_search_history_creation(self, async_session):
        """Test creating a search history entry."""
        user = User(
            id=uuid4(),
            email="searcher@example.com",
            username="searcher",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        search = SearchHistory(
            id=uuid4(),
            user_id=user.id,
            query="machine learning transformers",
            params={"limit": 10, "include_foundations": True},
            result_count=5,
            created_at=datetime.now(timezone.utc)
        )
        
        async_session.add(user)
        async_session.add(search)
        await async_session.commit()
        
        assert search.id is not None
        assert search.user_id == user.id
        assert search.query == "machine learning transformers"
        assert search.params["limit"] == 10
        assert search.result_count == 5
    
    @pytest.mark.asyncio
    async def test_search_history_with_json_params(self, async_session):
        """Test search history with complex JSON params."""
        user = User(
            id=uuid4(),
            email="advanced@example.com",
            username="advanced",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        search = SearchHistory(
            id=uuid4(),
            user_id=user.id,
            query="neural networks",
            params={
                "limit": 20,
                "filters": {
                    "categories": ["cs.AI", "cs.LG"],
                    "min_citations": 10
                },
                "sort_by": "relevance"
            },
            result_count=15,
            created_at=datetime.now(timezone.utc)
        )
        
        async_session.add(user)
        async_session.add(search)
        await async_session.commit()
        
        assert isinstance(search.params, dict)
        assert search.params["filters"]["categories"] == ["cs.AI", "cs.LG"]
        assert search.params["filters"]["min_citations"] == 10
    
    @pytest.mark.asyncio
    async def test_multiple_search_history_entries(self, async_session):
        """Test multiple search history entries for same user."""
        user = User(
            id=uuid4(),
            email="frequent@example.com",
            username="frequent",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        search1 = SearchHistory(
            id=uuid4(),
            user_id=user.id,
            query="first search",
            params={},
            result_count=3,
            created_at=datetime.now(timezone.utc)
        )
        
        search2 = SearchHistory(
            id=uuid4(),
            user_id=user.id,
            query="second search",
            params={},
            result_count=7,
            created_at=datetime.now(timezone.utc)
        )
        
        async_session.add(user)
        async_session.add(search1)
        async_session.add(search2)
        await async_session.commit()
        
        assert search1.user_id == search2.user_id
        assert search1.query != search2.query
