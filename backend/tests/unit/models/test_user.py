import pytest
from src.models.user import User, UserPreferences


@pytest.mark.unit
class TestUserModel:
    """Tests for the User model."""
    
    def test_user_creation(self, sample_user_data):
        """Test creating a user with valid data."""
        user = User(**sample_user_data)
        
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_verified is True
    
    @pytest.mark.asyncio
    async def test_user_persistence(self, async_session, sample_user_data):
        """Test saving and retrieving user from database."""
        user = User(**sample_user_data)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.created_at is not None
    
    @pytest.mark.asyncio
    async def test_user_unique_email(self, async_session, sample_user_data):
        """Test that email must be unique."""
        from sqlalchemy.exc import IntegrityError
        
        user1 = User(**sample_user_data)
        async_session.add(user1)
        await async_session.commit()
        
        user2_data = {**sample_user_data, "username": "different"}
        user2 = User(**user2_data)
        async_session.add(user2)
        
        with pytest.raises(IntegrityError):
            await async_session.commit()
    
    @pytest.mark.asyncio
    async def test_user_unique_username(self, async_session, sample_user_data):
        """Test that username must be unique."""
        from sqlalchemy.exc import IntegrityError
        
        user1 = User(**sample_user_data)
        async_session.add(user1)
        await async_session.commit()
        
        user2_data = {**sample_user_data, "email": "different@example.com"}
        user2 = User(**user2_data)
        async_session.add(user2)
        
        with pytest.raises(IntegrityError):
            await async_session.commit()


@pytest.mark.unit
class TestUserPreferencesModel:
    """Tests for the UserPreferences model."""
    
    @pytest.mark.asyncio
    async def test_preferences_creation(self, async_session, test_user):
        """Test creating user preferences."""
        prefs = UserPreferences(
            user_id=test_user.id,
            preferred_categories=["cs.AI", "cs.LG"],
            theme="dark",
            default_search_limit="20",
        )
        async_session.add(prefs)
        await async_session.commit()
        await async_session.refresh(prefs)
        
        assert prefs.id is not None
        assert prefs.user_id == test_user.id
        assert len(prefs.preferred_categories) == 2
        assert prefs.theme == "dark"
    
    @pytest.mark.asyncio
    async def test_preferences_defaults(self, async_session, test_user):
        """Test default values for preferences."""
        prefs = UserPreferences(user_id=test_user.id)
        async_session.add(prefs)
        await async_session.commit()
        await async_session.refresh(prefs)
        
        assert prefs.preferred_categories == []
        assert prefs.theme == "light"
        assert prefs.items_per_page == "10"
        assert prefs.email_notifications is True
        assert prefs.default_context_strategy == "trimming"
    
    @pytest.mark.asyncio
    async def test_preferences_relationship(self, async_session, test_user):
        """Test relationship between User and UserPreferences."""
        prefs = UserPreferences(
            user_id=test_user.id,
            preferred_categories=["cs.AI"],
        )
        async_session.add(prefs)
        await async_session.commit()
        await async_session.refresh(test_user)
        assert prefs.user_id == test_user.id
    
    @pytest.mark.asyncio
    async def test_preferences_cascade_delete(self, async_session, test_user):
        """Test that preferences are deleted when user is deleted."""
        prefs = UserPreferences(user_id=test_user.id)
        async_session.add(prefs)
        await async_session.commit()
        
        prefs_id = prefs.id
        
        await async_session.delete(test_user)
        await async_session.commit()
        
        from sqlalchemy import select
        result = await async_session.execute(
            select(UserPreferences).where(UserPreferences.id == prefs_id)
        )
        assert result.scalar_one_or_none() is None
