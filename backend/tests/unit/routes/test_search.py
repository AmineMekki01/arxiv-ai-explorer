import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from src.main import app


client = TestClient(app)


@pytest.mark.unit
class TestSearchRoutes:
    """Tests for search API endpoints."""
    
    @patch('src.routes.search.get_graph_enhanced_retriever')
    def test_enhanced_search_post(self, mock_retriever):
        """Test POST /search/enhanced endpoint."""
        mock_retriever_instance = AsyncMock()
        mock_retriever_instance.search = AsyncMock(return_value={
            "results": [
                {
                    "arxiv_id": "2301.00001",
                    "title": "Test Paper",
                    "chunks": [{"chunk_text": "Test chunk", "score": 0.9}],
                    "graph_metadata": {
                        "citation_count": 10,
                        "is_seminal": False,
                        "cited_by_results": 0,
                        "is_foundational": False
                    },
                    "max_score": 0.9
                }
            ],
            "graph_insights": {
                "total_papers": 1,
                "internal_citations": 0,
                "foundational_papers_added": 0,
                "central_papers": []
            },
            "query": "test query"
        })
        mock_retriever.return_value = mock_retriever_instance
        
        response = client.post(
            "/search/enhanced",
            json={
                "query": "test query",
                "limit": 10,
                "include_foundations": True,
                "min_foundation_citations": 3
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "graph_insights" in data
        assert data["query"] == "test query"
        assert len(data["results"]) == 1
    
    @patch('src.routes.search.get_graph_enhanced_retriever')
    def test_enhanced_search_get(self, mock_retriever):
        """Test GET /search/enhanced endpoint."""
        mock_retriever_instance = AsyncMock()
        mock_retriever_instance.search = AsyncMock(return_value={
            "results": [],
            "graph_insights": {
                "total_papers": 0,
                "internal_citations": 0,
                "foundational_papers_added": 0,
                "central_papers": []
            },
            "query": "test"
        })
        mock_retriever.return_value = mock_retriever_instance
        
        response = client.get(
            "/search/enhanced?query=test&limit=5&include_foundations=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
    
    def test_enhanced_search_validation(self):
        """Test request validation."""
        response = client.post("/search/enhanced", json={"limit": 10})
        assert response.status_code == 422
        
        response = client.post(
            "/search/enhanced",
            json={"query": "test", "limit": 1000}
        )
        assert response.status_code == 422
        
        response = client.post(
            "/search/enhanced",
            json={"query": "test", "limit": 0}
        )
        assert response.status_code == 422
    
    @patch('src.routes.search.get_graph_enhanced_retriever')
    def test_enhanced_search_error_handling(self, mock_retriever):
        """Test error handling in search endpoint."""
        mock_retriever_instance = AsyncMock()
        mock_retriever_instance.search = AsyncMock(side_effect=Exception("Search failed"))
        mock_retriever.return_value = mock_retriever_instance
        
        response = client.post(
            "/search/enhanced",
            json={"query": "test", "limit": 10}
        )
        
        assert response.status_code == 500
        assert "Search failed" in response.json()["detail"]
    
    @patch('src.routes.search.get_current_user')
    @patch('src.routes.search.get_graph_enhanced_retriever')
    @patch('src.routes.search.get_sync_session')
    def test_search_history_logging(self, mock_session, mock_retriever, mock_user):
        """Test that search history is logged for authenticated users."""
        mock_user.return_value = MagicMock(id="user-123")
        
        mock_retriever_instance = AsyncMock()
        mock_retriever_instance.search = AsyncMock(return_value={
            "results": [],
            "graph_insights": {
                "total_papers": 0,
                "internal_citations": 0,
                "foundational_papers_added": 0,
                "central_papers": []
            },
            "query": "test"
        })
        mock_retriever.return_value = mock_retriever_instance
        
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        
        response = client.post(
            "/search/enhanced",
            json={"query": "test", "limit": 10},
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == 200