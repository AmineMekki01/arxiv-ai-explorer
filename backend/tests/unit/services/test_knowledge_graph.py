import pytest
from unittest.mock import Mock
from datetime import datetime, timezone
from src.services.knowledge_graph.graph_builder import KnowledgeGraphBuilder
from src.services.knowledge_graph.neo4j_client import Neo4jClient
from src.models.paper import Paper

@pytest.fixture
def mock_neo4j_client():
    """Create a mock Neo4j client."""
    client = Mock(spec=Neo4jClient)
    return client

@pytest.fixture
def graph_builder(mock_neo4j_client):
    """Create a KnowledgeGraphBuilder instance."""
    return KnowledgeGraphBuilder(mock_neo4j_client)

@pytest.fixture
def sample_paper():
    """Create a sample Paper object."""
    return Paper(
        arxiv_id="2301.00001v1",
        title="Test Paper",
        abstract="Abstract",
        published_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
        updated_date=datetime(2023, 1, 2, tzinfo=timezone.utc),
        primary_category="cs.AI",
        categories=["cs.AI", "cs.LG"],
        authors=["Author A", "Author B"],
        affiliations=["Inst A", "Inst B"],
        citation_count=10,
        reference_count=5,
        influential_citation_count=2,
        references=[
            {"arxiv_id": "2201.00001", "title": "Ref 1", "is_influential": True},
            {"doi": "10.1234/doi", "title": "Ref 2"}
        ],
        cited_by=[
            {"arxiv_id": "2401.00001", "title": "Citing 1"}
        ]
    )

class TestKnowledgeGraphBuilder:
    """Tests for KnowledgeGraphBuilder."""

    def test_init(self, graph_builder, mock_neo4j_client):
        """Test initialization."""
        assert graph_builder.client == mock_neo4j_client

    def test_create_paper_node(self, graph_builder, mock_neo4j_client, sample_paper):
        """Test creating paper node."""
        mock_neo4j_client.execute_write.return_value = {"nodes_created": 1}
        
        result = graph_builder.create_paper_node(sample_paper)
        
        assert result["nodes_created"] == 1
        mock_neo4j_client.execute_write.assert_called_once()
        args = mock_neo4j_client.execute_write.call_args
        assert "MERGE (p:Paper" in args[0][0]
        assert args[0][1]["arxiv_id"] == "2301.00001"

    def test_create_category_hierarchy(self, graph_builder, mock_neo4j_client, sample_paper):
        """Test creating category hierarchy."""
        mock_neo4j_client.execute_write.return_value = {"nodes_created": 2}
        
        result = graph_builder.create_category_hierarchy(sample_paper)
        
        assert result["nodes_created"] == 2
        mock_neo4j_client.execute_write.assert_called_once()
        args = mock_neo4j_client.execute_write.call_args
        assert "MERGE (mc:MainCategory" in args[0][0]
        assert len(args[0][1]["categories"]) == 2

    def test_create_author_nodes(self, graph_builder, mock_neo4j_client, sample_paper):
        """Test creating author nodes."""
        mock_neo4j_client.execute_write.return_value = {"nodes_created": 2}
        
        result = graph_builder.create_author_nodes(sample_paper)
        
        assert result["nodes_created"] == 2
        mock_neo4j_client.execute_write.assert_called_once()
        args = mock_neo4j_client.execute_write.call_args
        assert "MERGE (a:Author" in args[0][0]
        assert len(args[0][1]["authors"]) == 2

    def test_create_institution_nodes(self, graph_builder, mock_neo4j_client, sample_paper):
        """Test creating institution nodes."""
        mock_neo4j_client.execute_write.return_value = {"nodes_created": 2}
        
        result = graph_builder.create_institution_nodes(sample_paper)
        
        assert result["nodes_created"] == 2
        mock_neo4j_client.execute_write.assert_called_once()
        args = mock_neo4j_client.execute_write.call_args
        assert "MERGE (i:Institution" in args[0][0]
        assert len(args[0][1]["affiliations"]) == 2

    def test_create_year_node(self, graph_builder, mock_neo4j_client, sample_paper):
        """Test creating year node."""
        mock_neo4j_client.execute_write.return_value = {"nodes_created": 1}
        
        result = graph_builder.create_year_node(sample_paper)
        
        assert result["nodes_created"] == 1
        mock_neo4j_client.execute_write.assert_called_once()
        args = mock_neo4j_client.execute_write.call_args
        assert "MERGE (y:Year" in args[0][0]
        assert args[0][1]["year"] == 2023

    def test_create_citation_relationships(self, graph_builder, mock_neo4j_client, sample_paper):
        """Test creating citation relationships."""
        mock_neo4j_client.execute_write.return_value = {"relationships_created": 2}
        
        result = graph_builder.create_citation_relationships(sample_paper)
        
        assert result["relationships_created"] == 2
        mock_neo4j_client.execute_write.assert_called_once()
        args = mock_neo4j_client.execute_write.call_args
        assert "MERGE (citing)-[r:CITES]->(cited)" in args[0][0]
        assert len(args[0][1]["citations"]) == 2

    def test_create_reverse_citations(self, graph_builder, mock_neo4j_client, sample_paper):
        """Test creating reverse citation relationships."""
        mock_neo4j_client.execute_write.return_value = {"relationships_created": 1}
        
        result = graph_builder.create_reverse_citations(sample_paper)
        
        assert result["relationships_created"] == 1
        mock_neo4j_client.execute_write.assert_called_once()
        args = mock_neo4j_client.execute_write.call_args
        assert "MERGE (citing)-[r:CITES]->(cited)" in args[0][0]
        assert len(args[0][1]["citing_papers"]) == 1

    def test_build_full_graph(self, graph_builder, mock_neo4j_client, sample_paper):
        """Test building full graph."""
        mock_neo4j_client.execute_write.side_effect = [
            {"nodes_created": 1},
            {"nodes_created": 2, "relationships_created": 2},
            {"nodes_created": 2, "relationships_created": 2},
            {"nodes_created": 2, "relationships_created": 2},
            {"nodes_created": 1, "relationships_created": 1},
            {"relationships_created": 2},
            {"relationships_created": 1}
        ]
        
        summary = graph_builder.build_full_graph(sample_paper)
        
        assert summary["arxiv_id"] == "2301.00001v1"
        assert summary["nodes_created"] == 8
        assert summary["relationships_created"] == 10
        assert mock_neo4j_client.execute_write.call_count == 7

    def test_error_handling(self, graph_builder, mock_neo4j_client, sample_paper):
        """Test error handling in builder methods."""
        mock_neo4j_client.execute_write.side_effect = Exception("DB Error")
        
        with pytest.raises(Exception):
            graph_builder.create_paper_node(sample_paper)
            
        with pytest.raises(Exception):
            graph_builder.build_full_graph(sample_paper)
