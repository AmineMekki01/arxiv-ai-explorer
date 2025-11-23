import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.models.user import User


@pytest.mark.unit
class TestInteractionsRoutes:
    """Tests for paper interactions endpoints."""
    
    def test_save_paper_without_auth(self):
        """Test saving paper without authentication."""
        client = TestClient(app)
        response = client.post("/api/papers/save", json={"arxiv_id": "2301.00001"})
        assert response.status_code == 401
    
    def test_save_paper_success(self):
        """Test saving a paper successfully."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()
        
        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.save_paper.return_value = {"id": "save123", "arxiv_id": "2301.00001"}
            MockService.return_value = mock_instance
            
            response = client.post("/api/papers/save", json={
                "arxiv_id": "2301.00001",
                "paper_title": "Test Paper",
                "notes": "Interesting paper"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["arxiv_id"] == "2301.00001"
        
        app.dependency_overrides.clear()
    
    def test_unsave_paper_success(self):
        """Test unsaving a paper."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()
        
        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.unsave_paper.return_value = True
            MockService.return_value = mock_instance
            
            response = client.delete("/api/papers/save/2301.00001")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
        
        app.dependency_overrides.clear()
    
    def test_unsave_paper_not_found(self):
        """Test unsaving non-existent save."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()
        
        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.unsave_paper.return_value = False
            MockService.return_value = mock_instance
            
            response = client.delete("/api/papers/save/2301.99999")
            
            assert response.status_code == 404
        
        app.dependency_overrides.clear()
    
    def test_get_saved_papers(self):
        """Test getting saved papers."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()
        
        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.get_saved_papers.return_value = []
            MockService.return_value = mock_instance
            
            response = client.get("/api/papers/save")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
        
        app.dependency_overrides.clear()
    
    def test_check_if_saved(self):
        """Test checking if paper is saved."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()
        
        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.is_saved.return_value = True
            MockService.return_value = mock_instance
            
            response = client.get("/api/papers/save/2301.00001/check")
            
            assert response.status_code == 200
            data = response.json()
            assert data["is_saved"] == True
        
        app.dependency_overrides.clear()
    
    def test_like_paper_success(self):
        """Test liking a paper."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()
        
        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.like_paper.return_value = {"id": "like123"}
            MockService.return_value = mock_instance
            
            response = client.post("/api/papers/like", json={"arxiv_id": "2301.00001"})
            
            assert response.status_code == 200
        
        app.dependency_overrides.clear()
    
    def test_unlike_paper_success(self):
        """Test unliking a paper."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()
        
        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.unlike_paper.return_value = True
            MockService.return_value = mock_instance
            
            response = client.delete("/api/papers/like/2301.00001")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
        
        app.dependency_overrides.clear()
    
    def test_check_if_liked(self):
        """Test checking if paper is liked."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()
        
        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.is_liked.return_value = False
            MockService.return_value = mock_instance
            
            response = client.get("/api/papers/like/2301.00001/check")
            
            assert response.status_code == 200
            data = response.json()
            assert data["is_liked"] == False
        
        app.dependency_overrides.clear()
    
    def test_track_view(self):
        """Test tracking a paper view."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()
        
        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.track_view.return_value = None
            MockService.return_value = mock_instance
            
            response = client.post("/api/papers/view", json={
                "arxiv_id": "2301.00001",
                "duration_seconds": 120
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
        
        app.dependency_overrides.clear()
    
    def test_get_liked_papers(self):
        """Test getting liked papers."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()
        
        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.get_liked_papers.return_value = []
            MockService.return_value = mock_instance
            
            response = client.get("/api/papers/like")
            
            assert response.status_code == 200
            assert isinstance(response.json(), list)
        
        app.dependency_overrides.clear()

    def test_track_view_error(self):
        """track_view should return error payload when service raises."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()

        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.track_view.side_effect = RuntimeError("boom")
            MockService.return_value = mock_instance

            response = client.post(
                "/api/papers/view",
                json={"arxiv_id": "2301.00001", "duration_seconds": 10},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "boom" in data["message"]

        app.dependency_overrides.clear()

    def test_get_paper_stats_success(self):
        """Test getting paper stats successfully."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()

        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.get_paper_stats.return_value = {
                "arxiv_id": "2301.00001",
                "likes": 1,
                "views_total": 2,
                "views_7d": 1,
                "saves": 3,
                "user_saved": True,
                "user_liked": False,
            }
            MockService.return_value = mock_instance

            response = client.get("/api/papers/2301.00001/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["arxiv_id"] == "2301.00001"
            assert data["likes"] == 1

        app.dependency_overrides.clear()

    def test_get_paper_stats_error(self):
        """get_paper_stats should return 500 when service raises."""
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
        from src.routes.interactions import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: MagicMock()

        with patch("src.routes.interactions.PaperInteractionService") as MockService:
            mock_instance = MagicMock()
            mock_instance.get_paper_stats.side_effect = RuntimeError("boom")
            MockService.return_value = mock_instance

            response = client.get("/api/papers/2301.00001/stats")

            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "boom"

        app.dependency_overrides.clear()

    def test_get_user_stats_basic(self):
        """Test get_user_stats aggregates counts and preferences from DB."""
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
        mock_db = MagicMock()

        def make_count(value):
            q = MagicMock()
            f = MagicMock()
            f.scalar.return_value = value
            q.filter.return_value = f
            return q

        def make_user_views():
            q = MagicMock()
            f = MagicMock()
            view = MagicMock()
            view.arxiv_id = "2301.00001"
            f.all.return_value = [view]
            q.filter.return_value = f
            return q

        def make_authors_rows():
            q = MagicMock()
            f = MagicMock()
            f.all.return_value = [
                (["Author A", "Author B"], ["cs.AI", "cs.LG"]),
            ]
            q.filter.return_value = f
            return q

        mock_db.query.side_effect = [
            make_count(1),
            make_count(2),
            make_count(3),
            make_user_views(),
            make_authors_rows(),
        ]

        from src.routes.auth import require_auth
        from src.routes.interactions import provide_sync_session

        app.dependency_overrides[require_auth] = lambda: mock_user
        app.dependency_overrides[provide_sync_session] = lambda: mock_db

        response = client.get("/api/papers/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["saves_count"] == 1
        assert data["likes_count"] == 2
        assert data["views_count"] == 3
        assert data["interactions_count"] == 6
        assert "cs.AI" in data["preferred_categories"]
        assert "Author A" in data["preferred_authors"]

        app.dependency_overrides.clear()
