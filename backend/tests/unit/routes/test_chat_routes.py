import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.models.user import User


@pytest.mark.unit
class TestChatRoutes:
    """Tests for chat endpoints."""
    
    def test_list_chats_without_auth(self):
        """Test listing chats without authentication."""
        client = TestClient(app)
        response = client.get("/chats")
        assert response.status_code == 401
    
    def test_list_chats_success(self):
        """Test listing chats successfully."""
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
        
        mock_chats = [
            {"id": "chat1", "name": "Chat 1", "created_at": "2023-01-01T00:00:00Z"},
            {"id": "chat2", "name": "Chat 2", "created_at": "2023-01-02T00:00:00Z"}
        ]
        
        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        with patch("src.routes.chat.chat_store") as mock_store:
            mock_store.list_chats.return_value = mock_chats
            
            response = client.get("/chats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["items"]) == 2
            mock_store.list_chats.assert_called_once_with(user_id=str(mock_user.id))
        
        app.dependency_overrides.clear()
    
    def test_create_chat_success(self):
        """Test creating a new chat."""
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
        
        mock_chat = {"id": "new_chat", "name": "New Chat", "created_at": "2023-01-01T00:00:00Z"}
        
        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        with patch("src.routes.chat.chat_store") as mock_store:
            mock_store.create_chat.return_value = mock_chat
            
            response = client.post("/chats", json={"name": "New Chat"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["chat"]["id"] == "new_chat"
            mock_store.create_chat.assert_called_once_with(name="New Chat", user_id=str(mock_user.id))
        
        app.dependency_overrides.clear()
    
    def test_rename_chat_success(self):
        """Test renaming a chat."""
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
        
        with patch("src.routes.chat.chat_store") as mock_store:
            mock_store.rename_chat.return_value = True
            
            response = client.post("/chats/chat1/rename", json={"name": "Renamed Chat"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["name"] == "Renamed Chat"
        
        app.dependency_overrides.clear()
    
    def test_rename_chat_not_found(self):
        """Test renaming a non-existent chat."""
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
        
        with patch("src.routes.chat.chat_store") as mock_store:
            mock_store.rename_chat.return_value = False
            
            response = client.post("/chats/chat1/rename", json={"name": "Renamed Chat"})
            
            assert response.status_code == 404
        
        app.dependency_overrides.clear()
    
    def test_delete_chat_success(self):
        """Test deleting a chat."""
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
        
        with patch("src.routes.chat.chat_store") as mock_store, \
             patch("src.routes.chat.retrieval_agent") as mock_agent:
            
            mock_store.delete_chat.return_value = True
            mock_agent.delete_chat = AsyncMock()
            
            response = client.delete("/chats/chat1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            mock_agent.delete_chat.assert_called_once_with("chat1")
        
        app.dependency_overrides.clear()
    
    def test_get_messages_success(self):
        """Test getting messages from a chat."""
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
        
        mock_messages = [
            {"id": "msg1", "role": "user", "content": "Hello"},
            {"id": "msg2", "role": "assistant", "content": "Hi there"}
        ]
        
        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        with patch("src.routes.chat.chat_store") as mock_store:
            mock_store.list_messages.return_value = mock_messages
            
            response = client.get("/chats/chat1/messages")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["messages"]) == 2
        
        app.dependency_overrides.clear()
    
    def test_send_message_success(self):
        """Test sending a message to the chat."""
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
        
        mock_chat = {"id": "chat1", "user_id": str(mock_user.id)}
        mock_assistant_msg = {"id": "msg2", "role": "assistant", "content": "Response"}
        
        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        with patch("src.routes.chat.chat_store") as mock_store, \
             patch("src.routes.chat.retrieval_agent") as mock_agent, \
             patch("src.routes.chat.get_sync_session") as mock_session:
            
            mock_store.get_chat.return_value = mock_chat
            mock_store.add_message.return_value = mock_assistant_msg
            
            mock_agent.process_query = AsyncMock(return_value={
                "response": "Response",
                "sources": [{"title": "Paper 1", "arxiv_id": "2301.00001"}],
                "graph_insights": {}
            })
            
            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            response = client.post("/chats/chat1/messages", json={
                "role": "user",
                "content": "Test query"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["message"]["content"] == "Response"
            
            mock_store.add_message.assert_called()
            mock_agent.process_query.assert_called_once()
        
        app.dependency_overrides.clear()

    def test_send_message_idempotency(self):
        """Test idempotency when sending message with client_msg_id."""
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
        
        mock_chat = {"id": "chat1", "user_id": str(mock_user.id)}
        client_msg_id = "client-123"
        
        existing_msgs = [
            {"id": "msg1", "role": "user", "content": "Test query", "client_msg_id": client_msg_id},
            {"id": "msg2", "role": "assistant", "content": "Existing Response", "client_msg_id": client_msg_id}
        ]
        
        from src.routes.auth import require_auth
        app.dependency_overrides[require_auth] = lambda: mock_user
        
        with patch("src.routes.chat.chat_store") as mock_store, \
             patch("src.routes.chat.retrieval_agent") as mock_agent:
            
            mock_store.get_chat.return_value = mock_chat
            mock_store.list_messages.return_value = existing_msgs
            
            response = client.post("/chats/chat1/messages", json={
                "role": "user",
                "content": "Test query",
                "client_msg_id": client_msg_id
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"]["content"] == "Existing Response"
            
            mock_agent.process_query.assert_not_called()
        
        app.dependency_overrides.clear()
