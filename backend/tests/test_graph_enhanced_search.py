"""
Tests for graph-enhanced search functionality.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.services.retrieval.graph_enhanced_retriever import GraphEnhancedRetriever


@pytest.fixture
def mock_retriever():
    """Mock base retriever."""
    retriever = Mock()
    retriever.vector_search.return_value = [
        {
            "arxiv_id": "2103.12345",
            "title": "Test Paper 1",
            "chunk_text": "Test content",
            "score": 0.9,
            "published_date": "2024-01-01"
        },
        {
            "arxiv_id": "2104.56789",
            "title": "Test Paper 2",
            "chunk_text": "Test content 2",
            "score": 0.8,
            "published_date": "2023-01-01"
        }
    ]
    return retriever


@pytest.fixture
def mock_graph_service():
    """Mock graph query service."""
    service = Mock()
    service.get_internal_citations.return_value = [
        {"source": "2104.56789", "target": "2103.12345"}
    ]
    service.find_missing_foundations.return_value = [
        {
            "arxiv_id": "1706.03762",
            "title": "Attention Is All You Need",
            "cited_by_results": 2,
            "total_citations": 95000
        }
    ]
    service.get_papers_metadata.return_value = {
        "2103.12345": {
            "citation_count": 450,
            "is_seminal": True,
            "cited_by_count": 100
        },
        "2104.56789": {
            "citation_count": 23,
            "is_seminal": False,
            "cited_by_count": 5
        }
    }
    return service


class TestGraphEnhancedRetriever:
    """Test graph-enhanced retrieval."""
    
    @pytest.mark.asyncio
    async def test_search_basic(self, mock_retriever, mock_graph_service):
        """Test basic search flow."""
        with patch('src.services.retrieval.graph_enhanced_retriever.Retriever', return_value=mock_retriever):
            with patch('src.services.retrieval.graph_enhanced_retriever.Neo4jClient'):
                with patch('src.services.retrieval.graph_enhanced_retriever.GraphQueryService', return_value=mock_graph_service):
                    retriever = GraphEnhancedRetriever()
                    results = await retriever.search("test query", limit=10)
                    
                    assert "results" in results
                    assert "graph_insights" in results
                    assert len(results["results"]) > 0
    
    def test_rerank_with_graph_boosts_seminal(self):
        """Test that seminal papers get boosted."""
        retriever = GraphEnhancedRetriever()
        
        chunks = [
            {"arxiv_id": "paper1", "score": 0.5, "published_date": "2023-01-01"},
            {"arxiv_id": "paper2", "score": 0.5, "published_date": "2023-01-01"}
        ]
        
        graph_insights = {
            "papers_metadata": {
                "paper1": {"is_seminal": True, "citation_count": 500},
                "paper2": {"is_seminal": False, "citation_count": 10}
            },
            "internal_citations": []
        }
        
        reranked = retriever._rerank_with_graph(chunks, graph_insights, "test")
        
        # Paper1 should be ranked higher due to seminal boost
        assert reranked[0]["arxiv_id"] == "paper1"
        assert reranked[0]["final_score"] > reranked[1]["final_score"]
    
    def test_rerank_boosts_central_papers(self):
        """Test that papers cited by others in results get boosted."""
        retriever = GraphEnhancedRetriever()
        
        chunks = [
            {"arxiv_id": "paper1", "score": 0.5, "published_date": "2023-01-01"},
            {"arxiv_id": "paper2", "score": 0.5, "published_date": "2023-01-01"}
        ]
        
        graph_insights = {
            "papers_metadata": {
                "paper1": {"is_seminal": False, "citation_count": 10},
                "paper2": {"is_seminal": False, "citation_count": 10}
            },
            "internal_citations": [
                {"source": "paper2", "target": "paper1"},
                {"source": "paper3", "target": "paper1"}
            ]
        }
        
        reranked = retriever._rerank_with_graph(chunks, graph_insights, "test")
        
        # Paper1 cited by 2 others should be ranked higher
        assert reranked[0]["arxiv_id"] == "paper1"
    
    def test_smart_select_ensures_diversity(self):
        """Test that smart selection includes diverse papers."""
        retriever = GraphEnhancedRetriever()
        
        chunks = [
            {"arxiv_id": "paper1", "title": "P1", "final_score": 0.9, "graph_metadata": {}},
            {"arxiv_id": "paper1", "title": "P1", "final_score": 0.85, "graph_metadata": {}},
            {"arxiv_id": "paper2", "title": "P2", "final_score": 0.7, "graph_metadata": {}},
            {"arxiv_id": "paper3", "title": "P3", "final_score": 0.6, "graph_metadata": {}}
        ]
        
        selected = retriever._smart_select(chunks, limit=3)
        
        # Should include at least 2 different papers
        unique_papers = set([c["arxiv_id"] for c in selected])
        assert len(unique_papers) >= 2
    
    def test_identify_central_papers(self):
        """Test identification of central papers."""
        retriever = GraphEnhancedRetriever()
        
        internal_citations = [
            {"source": "p1", "target": "p_central"},
            {"source": "p2", "target": "p_central"},
            {"source": "p3", "target": "p_other"}
        ]
        
        central = retriever._identify_central_papers(internal_citations)
        
        assert "p_central" in central
        assert "p_other" not in central  # Only cited by 1 paper


@pytest.mark.integration
class TestGraphEnhancedSearchEndpoint:
    """Integration tests for search endpoint."""
    
    @pytest.mark.asyncio
    async def test_enhanced_search_endpoint(self, client):
        """Test enhanced search API endpoint."""
        response = await client.post(
            "/search/enhanced",
            json={
                "query": "transformer efficiency",
                "limit": 5,
                "include_foundations": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert "graph_insights" in data
        assert "query" in data
        assert data["query"] == "transformer efficiency"
    
    @pytest.mark.asyncio
    async def test_comparison_endpoint(self, client):
        """Test comparison endpoint."""
        response = await client.post(
            "/search/compare?query=transformers&limit=5"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "standard_results" in data
        assert "enhanced_results" in data
        assert "query" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
