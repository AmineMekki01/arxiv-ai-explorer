import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime
from uuid import uuid4

from src.main import app
from src.models.user import User
from src.routes.auth import get_current_user, require_auth


@pytest.mark.unit
class TestAuthRoutes:
    """Tests for authentication API endpoints."""
    
    def test_register_validation(self):
        """Test registration input validation."""
        client = TestClient(app)
        
        response = client.post("/auth/register", json={"email": "test@example.com"})
        assert response.status_code == 422
        
        response = client.post("/auth/register", json={
            "email": "invalid-email",
            "username": "testuser",
            "password": "password123"
        })
        assert response.status_code == 422
        
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "short"
        })
        assert response.status_code == 422
    
    def test_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without authentication."""
        client = TestClient(app)
        
        response = client.get("/auth/me")
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()
    
    @patch('src.routes.auth.get_sync_session')
    def test_register_success(self, mock_get_session):
        """Test successful user registration."""
        client = TestClient(app)
        
        mock_db = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.post("/auth/register", json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "password123",
            "full_name": "New User"
        })
        
        assert response.status_code == 201
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"
        assert "user" in response.json()
    
    @patch('src.routes.auth.get_sync_session')
    def test_register_duplicate_email(self, mock_get_session):
        """Test registration with existing email."""
        client = TestClient(app)
        
        existing_user = MagicMock()
        existing_user.email = "existing@example.com"
        existing_user.username = "otheruser"
        
        mock_db = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user
        
        response = client.post("/auth/register", json={
            "email": "existing@example.com",
            "username": "newuser",
            "password": "password123"
        })
        
        assert response.status_code == 400
        assert "email already registered" in response.json()["detail"].lower()
    
    @patch('src.routes.auth.get_sync_session')
    @patch('src.routes.auth.verify_password')
    def test_login_success(self, mock_verify, mock_get_session):
        """Test successful login."""
        client = TestClient(app)
        
        mock_user = MagicMock()
        mock_user.id = str(uuid4())
        mock_user.email = "user@example.com"
        mock_user.username = "testuser"
        mock_user.full_name = "Test User"
        mock_user.is_active = True
        mock_user.is_verified = True
        mock_user.created_at = datetime.utcnow()
        mock_user.last_login = None
        mock_user.hashed_password = "hashed_password"
        
        mock_db = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_verify.return_value = True
        
        response = client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["user"]["email"] == "user@example.com"
    
    @patch('src.routes.auth.get_sync_session')
    @patch('src.routes.auth.verify_password')
    def test_login_invalid_credentials(self, mock_verify, mock_get_session):
        """Test login with invalid credentials."""
        client = TestClient(app)
        
        mock_user = MagicMock()
        mock_user.hashed_password = "hashed_password"
        
        mock_db = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        mock_verify.return_value = False

        response = client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    def test_protected_endpoint_with_valid_token(self):
        """Test accessing protected endpoint with valid token."""
        client = TestClient(app)
        
        mock_user = User(
            id=str(uuid4()),
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            full_name="Test User",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        try:
            response = client.get("/auth/me")
            assert response.status_code == 200
            assert response.json()["email"] == "test@example.com"
            assert response.json()["username"] == "testuser"
        finally:
            app.dependency_overrides.clear()
    
    def test_protected_endpoint_with_invalid_token(self):
        """Test accessing protected endpoint with invalid token."""
        client = TestClient(app)
        
        app.dependency_overrides[get_current_user] = lambda: None
        
        try:
            response = client.get("/auth/me")
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()
    
    def test_logout(self):
        """Test logout endpoint."""
        client = TestClient(app)
        
        mock_user = User(
            id=str(uuid4()),
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            full_name="Test User",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        try:
            response = client.post("/auth/logout")
            assert response.status_code == 200
            assert response.json()["status"] == "success"
        finally:
            app.dependency_overrides.clear()
