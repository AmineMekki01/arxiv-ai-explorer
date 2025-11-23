import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.models.user import User


@pytest.mark.unit
class TestHistoryRoutes:
    """Tests for history endpoints."""
    
    def test_list_history_without_auth(self):
        """Test listing history without authentication."""
        client = TestClient(app)
        response = client.get("/history")
        
        assert response.status_code == 401

    
    def test_list_history_success(self):
        """Test listing search history."""
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
        
        mock_history = [
            MagicMock(
                id=uuid4(),
                user_id=mock_user.id,
                query="machine learning",
                params={"limit": 10},
                created_at=datetime.now(timezone.utc)
            ),
            MagicMock(
                id=uuid4(),
                user_id=mock_user.id,
                query="neural networks",
                params={},
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        mock_history[0].results_count = "5"
        mock_history[1].results_count = "3"
        
        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        with patch("src.routes.history.get_sync_session") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_history
            
            response = client.get("/history")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["query"] == "machine learning"
            assert data[1]["query"] == "neural networks"
        
        app.dependency_overrides.clear()
    
    def test_list_history_with_limit(self):
        """Test listing history with custom limit."""
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
        
        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        with patch("src.routes.history.get_sync_session") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            
            response = client.get("/history?limit=50")
            
            assert response.status_code == 200
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.assert_called_once_with(50)
        
        app.dependency_overrides.clear()
    
    def test_clear_history_without_auth(self):
        """Test clearing history without authentication."""
        client = TestClient(app)
        response = client.delete("/history")
        
        assert response.status_code == 401
    
    def test_clear_history_success(self):
        """Test clearing all search history."""
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
        
        mock_history = [
            MagicMock(id=uuid4()),
            MagicMock(id=uuid4()),
            MagicMock(id=uuid4())
        ]
        
        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        with patch("src.routes.history.get_sync_session") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.all.return_value = mock_history
            
            response = client.delete("/history")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["deleted"] == 3
            
            assert mock_db.delete.call_count == 3
            mock_db.commit.assert_called_once()
        
        app.dependency_overrides.clear()
    
    def test_list_history_empty(self):
        """Test listing history when user has no history."""
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
        
        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        with patch("src.routes.history.get_sync_session") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db
            mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            
            response = client.get("/history")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 0
        
        app.dependency_overrides.clear()