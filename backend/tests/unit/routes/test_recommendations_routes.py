import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.models.user import User


@pytest.mark.unit
class TestRecommendationsRoutes:
    """Tests for recommendations API endpoints."""

    def _make_user(self) -> User:
        return User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
        )

    def test_get_recommendations_normalizes_strategies_and_calls_recommender(self):
        """Route should normalize strategies and forward them to PaperRecommender."""
        client = TestClient(app)

        mock_user = self._make_user()

        from src.routes.auth import require_auth
        from src.routes.recommendations import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        mock_db = MagicMock()
        app.dependency_overrides[provide_sync_session] = lambda: mock_db

        with patch("src.routes.recommendations.PaperRecommender") as MockRec, \
             patch("src.routes.recommendations.Neo4jClient") as MockNeo4j:

            neo_instance = MagicMock()
            MockNeo4j.return_value = neo_instance

            rec_instance = MagicMock()
            MockRec.return_value = rec_instance
            rec_instance.get_recommendations.return_value = [
                {
                    "arxiv_id": "2301.00001",
                    "title": "Recommended Paper",
                    "abstract": "",
                    "authors": ["Author 1"],
                    "published_date": "2023-01-01T00:00:00Z",
                    "categories": ["cs.AI"],
                    "citation_count": 10,
                    "recommendation_score": 0.95,
                    "thumbnail_url": "http://example.com/thumb.png",
                    "reasons": ["because reasons"],
                }
            ]

            response = client.get(
                "/api/recommendations?limit=5&offset=0&strategies=content,citation,unknown"
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert data[0]["arxiv_id"] == "2301.00001"

            rec_instance.get_recommendations.assert_called_once()
            kwargs = rec_instance.get_recommendations.call_args.kwargs
            assert kwargs["limit"] == 5
            assert kwargs["offset"] == 0
            assert kwargs["user_id"] == str(mock_user.id)
            assert kwargs["strategies"] == ["content", "graph"]

        app.dependency_overrides.clear()

    def test_get_recommendations_handles_neo4j_failure(self):
        """Route should still return recommendations when Neo4j connect fails."""
        client = TestClient(app)

        mock_user = self._make_user()

        from src.routes.auth import require_auth
        from src.routes.recommendations import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        mock_db = MagicMock()
        app.dependency_overrides[provide_sync_session] = lambda: mock_db

        with patch("src.routes.recommendations.PaperRecommender") as MockRec, \
             patch("src.routes.recommendations.Neo4jClient") as MockNeo4j:

            neo_instance = MagicMock()
            MockNeo4j.return_value = neo_instance
            neo_instance.connect.side_effect = RuntimeError("neo4j down")

            rec_instance = MagicMock()
            MockRec.return_value = rec_instance
            rec_instance.get_recommendations.return_value = []

            response = client.get("/api/recommendations?limit=3")

            assert response.status_code == 200
            assert response.json() == []

            rec_instance.get_recommendations.assert_called_once()

        app.dependency_overrides.clear()

    def test_get_recommendations_error_returns_500(self):
        """Route should wrap recommender errors into HTTP 500."""
        client = TestClient(app)

        mock_user = self._make_user()

        from src.routes.auth import require_auth
        from src.routes.recommendations import provide_sync_session
        app.dependency_overrides[require_auth] = lambda: mock_user
        mock_db = MagicMock()
        app.dependency_overrides[provide_sync_session] = lambda: mock_db

        with patch("src.routes.recommendations.PaperRecommender") as MockRec, \
             patch("src.routes.recommendations.Neo4jClient") as MockNeo4j:

            MockNeo4j.return_value = MagicMock()

            rec_instance = MagicMock()
            MockRec.return_value = rec_instance
            rec_instance.get_recommendations.side_effect = RuntimeError("recs boom")

            response = client.get("/api/recommendations")

            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "recs boom"

        app.dependency_overrides.clear()
