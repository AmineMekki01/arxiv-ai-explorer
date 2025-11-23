import asyncio
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.main import app
from src.models.user import User


@pytest.mark.unit
class TestAssistantRoutes:
    """Tests for assistant endpoints."""
    
    def test_get_session_info_success(self):
        """Test getting session info."""
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
        
        with patch("src.routes.assistant.chat_store") as mock_store, \
             patch("src.routes.assistant.retrieval_agent") as mock_agent:
            
            mock_store.get_chat.return_value = {"id": "chat1"}
            mock_agent.get_session_info = AsyncMock(return_value={"status": "active", "total_items": 5})
            
            response = client.get("/assistant/session/chat1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["session_info"]["total_items"] == 5
        
        app.dependency_overrides.clear()
    
    def test_query_agent_success(self):
        """Test querying the agent."""
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
        
        with patch("src.routes.assistant.chat_store") as mock_store, \
             patch("src.routes.assistant.retrieval_agent") as mock_agent, \
             patch("src.routes.assistant.get_sync_session") as mock_session:
            
            mock_store.get_chat.return_value = {"id": "chat1"}
            
            mock_agent.process_query = AsyncMock(return_value={
                "response": "Answer",
                "sources": [],
                "graph_insights": {}
            })
            mock_agent.get_session_info = AsyncMock(return_value={})
            
            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            response = client.get("/assistant?q=test&chat_id=chat1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["final_output"] == "Answer"
        
        app.dependency_overrides.clear()
    
    def test_clear_session_success(self):
        """Test clearing a session."""
        client = TestClient(app)
        
        with patch("src.routes.assistant.retrieval_agent") as mock_agent:
            mock_agent.clear_session = AsyncMock(return_value=True)
            
            response = client.delete("/assistant/session/chat1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    def test_switch_context_strategy(self):
        """Test switching context strategy."""
        client = TestClient(app)
        
        with patch("src.routes.assistant.retrieval_agent") as mock_agent:
            mock_agent.switch_context_strategy = AsyncMock(return_value=True)
            mock_agent.get_session_info = AsyncMock(return_value={})
            
            response = client.post("/assistant/session/chat1/strategy", json={"strategy": "summarization"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["new_strategy"] == "summarization"
    
    def test_list_available_strategies(self):
        """Test listing strategies."""
        client = TestClient(app)
        response = client.get("/assistant/strategies")
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data
        assert "trimming" in data["strategies"]
    
    def test_add_focused_paper(self):
        """Test adding a focused paper."""
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
        
        with patch("src.routes.assistant.chat_store") as mock_store, \
             patch("src.routes.assistant.retrieval_agent") as mock_agent:
            
            mock_store.get_chat.return_value = {"id": "chat1"}
            mock_agent.add_focused_paper = MagicMock()
            mock_agent.get_focused_papers.return_value = ["2301.00001"]
            
            response = client.post("/assistant/session/chat1/focus", json={
                "arxiv_id": "2301.00001",
                "title": "Test Paper"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "2301.00001" in data["focused_papers"]
        
        app.dependency_overrides.clear()
    
    def test_get_focused_papers(self):
        """Test getting focused papers."""
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
        
        with patch("src.routes.assistant.chat_store") as mock_store, \
             patch("src.routes.assistant.retrieval_agent") as mock_agent, \
             patch("src.services.knowledge_graph.Neo4jClient") as MockNeo4j:
            
            mock_store.get_chat.return_value = {"id": "chat1"}
            mock_agent.get_focused_papers.return_value = ["2301.00001"]
            
            mock_client = MagicMock()
            MockNeo4j.return_value.__enter__.return_value = mock_client
            mock_client.execute_query.return_value = [{"title": "Test Paper", "citations": 10}]
            
            response = client.get("/assistant/session/chat1/focus")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["focused_papers"]) == 1
            assert data["focused_papers"][0]["title"] == "Test Paper"
        
        app.dependency_overrides.clear()
    
    def test_get_paper_detail(self):
        """Test getting paper details."""
        client = TestClient(app)
        
        with patch("src.database.get_sync_session") as mock_session, \
             patch("src.services.knowledge_graph.Neo4jClient") as MockNeo4j, \
             patch("src.utils.arxiv_utils.normalize_arxiv_id") as mock_normalize:
            
            mock_normalize.return_value = "2301.00001"
            
            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            mock_paper = MagicMock()
            mock_paper.arxiv_id = "2301.00001"
            mock_paper.title = "Test Paper"
            mock_paper.abstract = "Abstract"
            mock_paper.authors = ["Author 1"]
            mock_paper.published_date = datetime.now(timezone.utc)
            mock_paper.updated_date = None
            mock_paper.primary_category = "cs.AI"
            mock_paper.categories = ["cs.AI"]
            
            mock_query = mock_db.query.return_value
            mock_filter = mock_query.filter.return_value
            mock_filter.first.return_value = mock_paper
            
            mock_client = MagicMock()
            MockNeo4j.return_value.__enter__.return_value = mock_client
            mock_client.execute_query.return_value = [{"citation_count": 5, "is_seminal": False}]
            
            response = client.get("/assistant/papers/2301.00001/detail")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["arxiv_id"] == "2301.00001"
            assert data["data"]["citation_count"] == 5

    def test_query_agent_chat_not_found(self):
        """query_agent should return 404 when chat is missing."""
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

        with patch("src.routes.assistant.chat_store") as mock_store, \
             patch("src.routes.assistant.retrieval_agent") as mock_agent:

            mock_store.get_chat.return_value = None

            response = client.get("/assistant?q=test&chat_id=chat1")

            assert response.status_code == 404
            data = response.json()
            assert "Chat not found" in data["detail"]

        app.dependency_overrides.clear()

    def test_query_agent_timeout(self):
        """query_agent should return 408 when processing times out."""
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

        with patch("src.routes.assistant.chat_store") as mock_store, \
             patch("src.routes.assistant.asyncio.wait_for") as mock_wait_for:

            mock_store.get_chat.return_value = {"id": "chat1"}
            mock_wait_for.side_effect = asyncio.TimeoutError()

            response = client.get("/assistant?q=test&chat_id=chat1")

            assert response.status_code == 408
            data = response.json()
            assert "timed out" in data["detail"].lower()

        app.dependency_overrides.clear()

    def test_query_agent_non_dict_result(self):
        """query_agent should handle non-dict results and still log history."""
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

        with patch("src.routes.assistant.chat_store") as mock_store, \
             patch("src.routes.assistant.retrieval_agent") as mock_agent, \
             patch("src.routes.assistant.get_sync_session") as mock_session:

            mock_store.get_chat.return_value = {"id": "chat1"}

            mock_agent.process_query = AsyncMock(return_value="Plain answer")
            mock_agent.get_session_info = AsyncMock(return_value={})

            mock_db = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_db

            response = client.get("/assistant?q=test&chat_id=chat1")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["final_output"] == "Plain answer"

        app.dependency_overrides.clear()

    def test_get_focused_papers_graph_error_fallback(self):
        """get_focused_papers should fall back to simple titles when Neo4j fails."""
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

        with patch("src.routes.assistant.chat_store") as mock_store, \
             patch("src.routes.assistant.retrieval_agent") as mock_agent, \
             patch("src.services.knowledge_graph.Neo4jClient") as MockNeo4j:

            mock_store.get_chat.return_value = {"id": "chat1"}
            mock_agent.get_focused_papers.return_value = ["2301.00001"]

            mock_client = MagicMock()
            MockNeo4j.return_value.__enter__.side_effect = Exception("graph down")

            response = client.get("/assistant/session/chat1/focus")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["focused_papers"][0]["title"] == "2301.00001"

        app.dependency_overrides.clear()

    def test_remove_focused_paper(self):
        """Test removing a focused paper."""
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

        with patch("src.routes.assistant.chat_store") as mock_store, \
             patch("src.routes.assistant.retrieval_agent") as mock_agent:

            mock_store.get_chat.return_value = {"id": "chat1"}
            mock_agent.remove_focused_paper = MagicMock()
            mock_agent.get_focused_papers.return_value = []

            response = client.delete("/assistant/session/chat1/focus/2301.00001")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["arxiv_id"] == "2301.00001"

        app.dependency_overrides.clear()

    def test_clear_focused_papers(self):
        """Test clearing all focused papers."""
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

        with patch("src.routes.assistant.chat_store") as mock_store, \
             patch("src.routes.assistant.retrieval_agent") as mock_agent:

            mock_store.get_chat.return_value = {"id": "chat1"}
            mock_agent.clear_focused_papers = MagicMock()

            response = client.delete("/assistant/session/chat1/focus")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["focused_count"] == 0

        app.dependency_overrides.clear()

    def test_get_strategy_recommendations(self):
        """Test getting strategy recommendations for a conversation type."""
        client = TestClient(app)

        with patch("src.routes.assistant.retrieval_agent") as mock_agent:
            mock_agent.get_strategy_recommendations.return_value = ["trimming"]

            response = client.get("/assistant/recommendations/research")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["conversation_type"] == "research"
            assert data["recommendations"] == ["trimming"]

    def test_get_strategy_recommendations_error(self):
        """get_strategy_recommendations should return 500 on internal error."""
        client = TestClient(app)

        with patch("src.routes.assistant.retrieval_agent") as mock_agent:
            mock_agent.get_strategy_recommendations.side_effect = RuntimeError("boom")

            response = client.get("/assistant/recommendations/research")

            assert response.status_code == 500
            data = response.json()
            assert "Failed to get recommendations" in data["detail"]
