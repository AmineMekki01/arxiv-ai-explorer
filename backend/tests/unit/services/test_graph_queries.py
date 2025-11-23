import pytest
from unittest.mock import Mock
from src.services.knowledge_graph.graph_queries import GraphQueryService
from src.services.knowledge_graph.neo4j_client import Neo4jClient

@pytest.fixture
def mock_neo4j_client():
    """Create a mock Neo4j client."""
    client = Mock(spec=Neo4jClient)
    return client

@pytest.fixture
def graph_service(mock_neo4j_client):
    """Create a GraphQueryService instance with mock client."""
    return GraphQueryService(mock_neo4j_client)

class TestGraphQueryService:
    """Tests for GraphQueryService."""

    def test_find_similar_papers_concept(self, graph_service, mock_neo4j_client):
        """Test finding similar papers by concept."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "arxiv_id": "2301.00002",
                "title": "Similar Paper",
                "published_date": "2023-01-02",
                "shared_concepts": 2,
                "concepts": ["cs.AI", "cs.LG"]
            }
        ]
        
        results = graph_service.find_similar_papers("2301.00001", method="concept")
        
        assert len(results) == 1
        assert results[0]["arxiv_id"] == "2301.00002"
        mock_neo4j_client.execute_query.assert_called_once()
        assert "BELONGS_TO_SUB" in mock_neo4j_client.execute_query.call_args[0][0]

    def test_find_similar_papers_author(self, graph_service, mock_neo4j_client):
        """Test finding similar papers by author."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "arxiv_id": "2301.00002",
                "title": "Similar Paper",
                "published_date": "2023-01-02",
                "shared_authors": 1,
                "authors": ["Author A"]
            }
        ]
        
        results = graph_service.find_similar_papers("2301.00001", method="author")
        
        assert len(results) == 1
        mock_neo4j_client.execute_query.assert_called_once()
        assert "AUTHORED_BY" in mock_neo4j_client.execute_query.call_args[0][0]

    def test_find_similar_papers_citation(self, graph_service, mock_neo4j_client):
        """Test finding similar papers by citation."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "arxiv_id": "2301.00002",
                "title": "Similar Paper",
                "published_date": "2023-01-02",
                "shared_citations": 5,
                "cited_papers": ["2201.00001"]
            }
        ]
        
        results = graph_service.find_similar_papers("2301.00001", method="citation")
        
        assert len(results) == 1
        mock_neo4j_client.execute_query.assert_called_once()
        assert "CITES" in mock_neo4j_client.execute_query.call_args[0][0]

    def test_find_similar_papers_combined(self, graph_service, mock_neo4j_client):
        """Test finding similar papers by combined method."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "arxiv_id": "2301.00002",
                "title": "Similar Paper",
                "published_date": "2023-01-02",
                "similarity_score": 10
            }
        ]
        
        results = graph_service.find_similar_papers("2301.00001", method="combined")
        
        assert len(results) == 1
        mock_neo4j_client.execute_query.assert_called_once()
        assert "similarity_score" in mock_neo4j_client.execute_query.call_args[0][0]

    def test_find_citation_network_depth_1(self, graph_service, mock_neo4j_client):
        """Test finding citation network at depth 1."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "cited_papers": [{"arxiv_id": "2201.00001"}],
                "citing_papers": [{"arxiv_id": "2401.00001"}]
            }
        ]
        
        result = graph_service.find_citation_network("2301.00001", depth=1)
        
        assert len(result["cited_papers"]) == 1
        assert len(result["citing_papers"]) == 1
        mock_neo4j_client.execute_query.assert_called_once()

    def test_find_citation_network_depth_2(self, graph_service, mock_neo4j_client):
        """Test finding citation network at depth 2."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "cited_papers": [{"arxiv_id": "2201.00001"}],
                "citing_papers": [{"arxiv_id": "2401.00001"}]
            }
        ]
        
        result = graph_service.find_citation_network("2301.00001", depth=2)
        
        assert len(result["cited_papers"]) == 1
        mock_neo4j_client.execute_query.assert_called_once()
        assert "*1..2" in mock_neo4j_client.execute_query.call_args[0][0]

    def test_find_research_path(self, graph_service, mock_neo4j_client):
        """Test finding research path."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "path": [
                    {"arxiv_id": "2301.00001", "title": "Start"},
                    {"arxiv_id": "2301.00002", "title": "End"}
                ]
            }
        ]
        
        result = graph_service.find_research_path("2301.00001", "2301.00002")
        
        assert len(result) == 2
        mock_neo4j_client.execute_query.assert_called_once()
        assert "shortestPath" in mock_neo4j_client.execute_query.call_args[0][0]

    def test_find_influential_papers(self, graph_service, mock_neo4j_client):
        """Test finding influential papers."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "arxiv_id": "2301.00001",
                "title": "Influential Paper",
                "citation_count": 100
            }
        ]
        
        results = graph_service.find_influential_papers(category="cs.AI")
        
        assert len(results) == 1
        mock_neo4j_client.execute_query.assert_called_once()
        assert "primary_category: $category" in mock_neo4j_client.execute_query.call_args[0][0]

    def test_find_trending_concepts(self, graph_service, mock_neo4j_client):
        """Test finding trending concepts."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "concept": "cs.AI",
                "paper_count": 50,
                "sample_papers": ["2301.00001"]
            }
        ]
        
        results = graph_service.find_trending_concepts()
        
        assert len(results) == 1
        mock_neo4j_client.execute_query.assert_called_once()

    def test_find_author_collaborations(self, graph_service, mock_neo4j_client):
        """Test finding author collaborations."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "collaborator": "Collaborator A",
                "collaboration_count": 5,
                "shared_papers": ["2301.00001"]
            }
        ]
        
        results = graph_service.find_author_collaborations("Author A")
        
        assert len(results) == 1
        mock_neo4j_client.execute_query.assert_called_once()

    def test_find_research_gaps(self, graph_service, mock_neo4j_client):
        """Test finding research gaps."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "arxiv_id": "2301.00001",
                "title": "Bridge Paper"
            }
        ]
        
        results = graph_service.find_research_gaps("cs.AI", "cs.LG")
        
        assert len(results) == 1
        mock_neo4j_client.execute_query.assert_called_once()

    def test_get_paper_context(self, graph_service, mock_neo4j_client):
        """Test getting paper context."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "arxiv_id": "2301.00001",
                "title": "Paper Title",
                "authors": ["Author A"],
                "categories": ["cs.AI"]
            }
        ]
        
        result = graph_service.get_paper_context("2301.00001")
        
        assert result["arxiv_id"] == "2301.00001"
        mock_neo4j_client.execute_query.assert_called_once()

    def test_get_internal_citations(self, graph_service, mock_neo4j_client):
        """Test getting internal citations."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "source": "2301.00001",
                "target": "2301.00002",
                "target_title": "Target Paper"
            }
        ]
        
        results = graph_service.get_internal_citations(["2301.00001", "2301.00002"])
        
        assert len(results) == 1
        mock_neo4j_client.execute_query.assert_called_once()

    def test_find_missing_foundations(self, graph_service, mock_neo4j_client):
        """Test finding missing foundations."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "arxiv_id": "2201.00001",
                "title": "Foundational Paper",
                "cited_by_results": 5
            }
        ]
        
        results = graph_service.find_missing_foundations(["2301.00001"])
        
        assert len(results) == 1
        mock_neo4j_client.execute_query.assert_called_once()

    def test_get_papers_metadata(self, graph_service, mock_neo4j_client):
        """Test getting papers metadata."""
        mock_neo4j_client.execute_query.return_value = [
            {
                "arxiv_id": "2301.00001",
                "citation_count": 10,
                "influential_citation_count": 2,
                "cited_by_count": 5,
                "published_date": "2023-01-01"
            }
        ]
        
        result = graph_service.get_papers_metadata(["2301.00001"])
        
        assert "2301.00001" in result
        assert result["2301.00001"]["citation_count"] == 10
        mock_neo4j_client.execute_query.assert_called_once()

    def test_error_handling(self, graph_service, mock_neo4j_client):
        """Test error handling in service methods."""
        mock_neo4j_client.execute_query.side_effect = Exception("DB Error")
        
        assert graph_service.find_similar_papers("2301.00001") == []
        assert graph_service.find_citation_network("2301.00001") == {"cited_papers": [], "citing_papers": []}
        assert graph_service.find_research_path("2301.00001", "2301.00002") == []
        assert graph_service.find_influential_papers() == []
        assert graph_service.find_trending_concepts() == []
        assert graph_service.find_author_collaborations("Author") == []
        assert graph_service.find_research_gaps("A", "B") == []
        assert graph_service.get_paper_context("2301.00001") == {}
        assert graph_service.get_internal_citations(["2301.00001"]) == []
        assert graph_service.find_missing_foundations(["2301.00001"]) == []
        assert graph_service.get_papers_metadata(["2301.00001"]) == {}
