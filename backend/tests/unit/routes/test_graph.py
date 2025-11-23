import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app


@pytest.mark.unit
class TestGraphRoutes:
    """Tests for knowledge graph endpoints."""
    
    def test_get_similar_papers(self):
        """Test getting similar papers."""
        client = TestClient(app)
        
        with patch("src.routes.graph.Neo4jClient") as MockClient, \
             patch("src.routes.graph.GraphQueryService") as MockService:
            
            mock_service = MagicMock()
            MockService.return_value = mock_service
            mock_service.find_similar_papers.return_value = [
                {
                    "arxiv_id": "2301.00001",
                    "title": "Similar Paper",
                    "similarity_score": 0.9,
                    "shared_concepts": 5,
                    "concepts": ["AI"],
                    "citation_count": 10,
                    "published_date": "2023-01-01"
                }
            ]
            
            response = client.get("/graph/papers/2301.00001/similar")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["arxiv_id"] == "2301.00001"
    
    def test_get_citation_network(self):
        """Test getting citation network."""
        client = TestClient(app)
        
        with patch("src.routes.graph.Neo4jClient") as MockClient, \
             patch("src.routes.graph.GraphQueryService") as MockService:
            
            mock_service = MagicMock()
            MockService.return_value = mock_service
            mock_service.find_citation_network.return_value = {
                "cited_papers": [{
                    "arxiv_id": "2301.00002",
                    "title": "Cited Paper",
                    "citation_count": 50
                }],
                "citing_papers": [{
                    "arxiv_id": "2301.00003",
                    "title": "Citing Paper",
                    "citation_count": 5
                }]
            }
            
            response = client.get("/graph/papers/2301.00001/citation-network")
            
            assert response.status_code == 200
            data = response.json()
            assert data["center_paper"] == "2301.00001"
            assert len(data["cited_papers"]) == 1
            assert len(data["citing_papers"]) == 1
    
    def test_find_research_path(self):
        """Test finding research path."""
        client = TestClient(app)
        
        with patch("src.routes.graph.Neo4jClient") as MockClient, \
             patch("src.routes.graph.GraphQueryService") as MockService:
            
            mock_service = MagicMock()
            MockService.return_value = mock_service
            mock_service.find_research_path.return_value = [
                {"arxiv_id": "2301.00001", "title": "Start"},
                {"arxiv_id": "2301.00002", "title": "End"}
            ]
            
            response = client.get("/graph/papers/path?from_arxiv_id=2301.00001&to_arxiv_id=2301.00002")
            
            assert response.status_code == 200
            data = response.json()
            assert data["length"] == 1
            assert len(data["path"]) == 2
    
    def test_get_influential_papers(self):
        """Test getting influential papers."""
        client = TestClient(app)
        
        with patch("src.routes.graph.Neo4jClient") as MockClient, \
             patch("src.routes.graph.GraphQueryService") as MockService:
            
            mock_service = MagicMock()
            MockService.return_value = mock_service
            mock_service.find_influential_papers.return_value = [
                {
                    "arxiv_id": "2301.00001",
                    "title": "Influential Paper",
                    "citation_count": 1000,
                    "pagerank_score": 0.95,
                    "authors": ["Author A"],
                    "published_date": "2023-01-01"
                }
            ]
            
            response = client.get("/graph/papers/influential")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["citation_count"] == 1000
    
    def test_get_trending_concepts(self):
        """Test getting trending concepts."""
        client = TestClient(app)
        
        with patch("src.routes.graph.Neo4jClient") as MockClient, \
             patch("src.routes.graph.GraphQueryService") as MockService:
            
            mock_service = MagicMock()
            MockService.return_value = mock_service
            mock_service.find_trending_concepts.return_value = [
                {
                    "concept": "LLM",
                    "paper_count": 500,
                    "sample_papers": ["2301.00001"]
                }
            ]
            
            response = client.get("/graph/concepts/trending")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["concept"] == "LLM"
    
    def test_get_author_collaborations(self):
        """Test getting author collaborations."""
        client = TestClient(app)
        
        with patch("src.routes.graph.Neo4jClient") as MockClient, \
             patch("src.routes.graph.GraphQueryService") as MockService:
            
            mock_service = MagicMock()
            MockService.return_value = mock_service
            mock_service.find_author_collaborations.return_value = [
                {
                    "collaborator": "Collaborator A",
                    "collaboration_count": 5,
                    "shared_papers": ["2301.00001"]
                }
            ]
            
            response = client.get("/graph/authors/Author%20Name/collaborations")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["collaborator"] == "Collaborator A"
    
    def test_find_research_gaps(self):
        """Test finding research gaps."""
        client = TestClient(app)
        
        with patch("src.routes.graph.Neo4jClient") as MockClient, \
             patch("src.routes.graph.GraphQueryService") as MockService:
            
            mock_service = MagicMock()
            MockService.return_value = mock_service
            mock_service.find_research_gaps.return_value = [
                {"arxiv_id": "2301.00001", "title": "Bridging Paper"}
            ]
            
            response = client.get("/graph/concepts/gaps?concept1=AI&concept2=Bio")
            
            assert response.status_code == 200
            data = response.json()
            assert data["concept1"] == "AI"
            assert len(data["bridging_papers"]) == 1
    
    def test_get_paper_context(self):
        """Test getting paper context."""
        client = TestClient(app)
        
        with patch("src.routes.graph.Neo4jClient") as MockClient, \
             patch("src.routes.graph.GraphQueryService") as MockService:
            
            mock_service = MagicMock()
            MockService.return_value = mock_service
            mock_service.get_paper_context.return_value = {
                "paper": {"arxiv_id": "2301.00001", "title": "Paper"},
                "authors": [{"name": "Author A"}],
                "concepts": [{"name": "Concept A"}]
            }
            
            response = client.get("/graph/papers/2301.00001/context")
            
            assert response.status_code == 200
            data = response.json()
            assert data["paper"]["arxiv_id"] == "2301.00001"

    def test_get_citation_network_empty_result(self):
        """get_citation_network should return empty lists when service returns no data."""
        client = TestClient(app)

        with patch("src.routes.graph.Neo4jClient") as MockClient, \
             patch("src.routes.graph.GraphQueryService") as MockService:

            mock_service = MagicMock()
            MockService.return_value = mock_service
            mock_service.find_citation_network.return_value = {}

            response = client.get("/graph/papers/2301.00001/citation-network?depth=3")

            assert response.status_code == 200
            data = response.json()
            assert data["center_paper"] == "2301.00001"
            assert data["depth"] == 3
            assert data["cited_papers"] == []
            assert data["citing_papers"] == []

    def test_get_citation_network_fallback_on_error(self):
        """get_citation_network should fall back to empty network on errors."""
        client = TestClient(app)

        with patch("src.routes.graph.Neo4jClient") as MockClient:
            MockClient.return_value.__enter__.side_effect = RuntimeError("boom")

            response = client.get("/graph/papers/2301.00001/citation-network?depth=2")

            assert response.status_code == 200
            data = response.json()
            assert data["center_paper"] == "2301.00001"
            assert data["depth"] == 2
            assert data["cited_papers"] == []
            assert data["citing_papers"] == []

    def test_find_research_path_not_found(self):
        """find_research_path should return 404 when no path exists."""
        client = TestClient(app)

        with patch("src.routes.graph.Neo4jClient") as MockClient, \
             patch("src.routes.graph.GraphQueryService") as MockService:

            mock_service = MagicMock()
            MockService.return_value = mock_service
            mock_service.find_research_path.return_value = []

            response = client.get("/graph/papers/path?from_arxiv_id=A&to_arxiv_id=B")

            assert response.status_code == 404

    def test_get_paper_context_not_found(self):
        """get_paper_context should return 404 when service returns no context."""
        client = TestClient(app)

        with patch("src.routes.graph.Neo4jClient") as MockClient, \
             patch("src.routes.graph.GraphQueryService") as MockService:

            mock_service = MagicMock()
            MockService.return_value = mock_service
            mock_service.get_paper_context.return_value = {}

            response = client.get("/graph/papers/2301.99999/context")

            assert response.status_code == 404

    def test_get_paper_context_error_returns_500(self):
        """get_paper_context should return 500 when service raises."""
        client = TestClient(app)

        with patch("src.routes.graph.Neo4jClient") as MockClient, \
             patch("src.routes.graph.GraphQueryService") as MockService:

            mock_service = MagicMock()
            MockService.return_value = mock_service
            mock_service.get_paper_context.side_effect = RuntimeError("boom")

            response = client.get("/graph/papers/2301.00001/context")

            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "boom"
