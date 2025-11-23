import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.models.user import User


@pytest.mark.unit
class TestPreferencesRoutes:
    """Tests for preferences endpoints."""
    
    def test_get_preferences_without_auth(self):
        """Test getting preferences without authentication."""
        client = TestClient(app)
        from src.routes.auth import require_auth
        from fastapi import HTTPException, status

        async def fake_require_auth():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        app.dependency_overrides[require_auth] = fake_require_auth

        response = client.get("/preferences")

        assert response.status_code == 401

        app.dependency_overrides.clear()
    
    def test_get_preferences_existing(self):
        """Test getting existing preferences."""
        client = TestClient(app)
        
        mock_user = User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        mock_prefs = MagicMock(
            id=uuid4(),
            user_id=mock_user.id,
            preferred_categories=["cs.AI", "cs.LG"],
            theme="dark",
            items_per_page="20",
            email_notifications=False,
            default_search_limit="20",
            default_context_strategy="advanced",
            custom_settings={"font_size": "16px"},
            updated_at=datetime.now(timezone.utc)
        )
        
        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        with patch("src.routes.preferences.get_sync_session") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = mock_prefs
            
            response = client.get("/preferences")
            
            assert response.status_code == 200
            data = response.json()
            assert data["theme"] == "dark"
            assert data["items_per_page"] == "20"
            assert data["email_notifications"] == False
            assert "cs.AI" in data["preferred_categories"]
            assert data["custom_settings"]["font_size"] == "16px"
        
        app.dependency_overrides.clear()
    
    def test_update_preferences_without_auth(self):
        """Test updating preferences without authentication."""
        client = TestClient(app)
        response = client.patch("/preferences", json={"theme": "dark"})
        
        assert response.status_code == 401
    
    def test_update_preferences_success(self):
        """Test updating user preferences."""
        client = TestClient(app)
        
        mock_user = User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        mock_prefs = MagicMock(
            id=uuid4(),
            user_id=mock_user.id,
            preferred_categories=[],
            theme="light",
            items_per_page="10",
            email_notifications=True,
            default_search_limit="10",
            default_context_strategy="trimming",
            custom_settings={},
            updated_at=datetime.now(timezone.utc)
        )
        
        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        with patch("src.routes.preferences.get_sync_session") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = mock_prefs
            
            response = client.patch("/preferences", json={
                "theme": "dark",
                "items_per_page": "25",
                "email_notifications": False
            })
            
            assert response.status_code == 200
            data = response.json()
            assert mock_prefs.theme == "dark"
            assert mock_prefs.items_per_page == "25"
            assert mock_prefs.email_notifications == False
            mock_db.commit.assert_called_once()
        
        app.dependency_overrides.clear()
    
    def test_get_available_categories(self):
        """Test getting available arXiv categories."""
        client = TestClient(app)
        
        response = client.get("/preferences/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0
        assert any(cat["code"] == "cs.AI" for cat in data["categories"])
        assert any(cat["code"] == "cs.LG" for cat in data["categories"])

    def test_get_preferences_creates_defaults_when_missing(self):
        """get_preferences should create default prefs when none exist."""
        client = TestClient(app)

        mock_user = User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user

        with patch("src.routes.preferences.get_sync_session") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            response = client.get("/preferences")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(mock_user.id)
        assert data["theme"] == "light"
        assert data["items_per_page"] == "10"
        assert data["email_notifications"] is True
        assert data["default_search_limit"] == "10"
        assert data["default_context_strategy"] == "trimming"

        app.dependency_overrides.clear()

    def test_update_preferences_not_found(self):
        """update_preferences should return 404 when prefs are missing."""
        client = TestClient(app)

        mock_user = User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user

        with patch("src.routes.preferences.get_sync_session") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            response = client.patch("/preferences", json={"theme": "dark"})

        assert response.status_code == 404

        app.dependency_overrides.clear()
