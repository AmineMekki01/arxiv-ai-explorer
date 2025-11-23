import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
import importlib


@pytest.fixture
def tools_module(monkeypatch):
    """Reload tools module with function_tool patched to identity for direct calling."""
    import agents

    def identity_decorator(fn):
        return fn

    monkeypatch.setattr(agents, "function_tool", identity_decorator)
    import src.agents.tools as tools
    importlib.reload(tools)
    return tools


@pytest.fixture
def mock_retriever(tools_module):
    """Mock GraphEnhancedRetriever."""
    with patch("src.agents.tools.graph_retriever") as mock:
        yield mock


@pytest.fixture
def mock_neo4j_client(tools_module):
    """Mock Neo4jClient."""
    with patch("src.services.knowledge_graph.Neo4jClient") as mock:
        yield mock


@pytest.fixture
def mock_db_session(tools_module):
    """Mock database session."""
    with patch("src.database.get_sync_session") as mock:
        session = MagicMock()
        mock.return_value.__enter__.return_value = session
        yield session


@pytest.mark.asyncio
async def test_search_papers_with_graph(mock_retriever, tools_module):
    """Test search_papers_with_graph tool."""
    mock_retriever.search = AsyncMock(return_value={
        "results": [{
            "arxiv_id": "2301.00001",
            "title": "Test Paper",
            "graph_metadata": {"citation_count": 10},
            "chunks": [{"chunk_text": "Sample text"}]
        }],
        "graph_insights": {"foundational": []}
    })

    tools_module.clear_tool_cache()

    result = tools_module.search_papers_with_graph(query="test", limit=5)

    assert result["tool_name"] == "search_papers_with_graph"
    assert len(result["results"]) == 1
    assert result["results"][0]["arxiv_id"] == "2301.00001"
    assert len(result["sources"]) == 1

    cached_results = tools_module.get_all_tool_results()
    assert len(cached_results) == 1
    assert cached_results[0] == result


@pytest.mark.asyncio
async def test_search_papers_with_graph_filters_ids(mock_retriever, tools_module):
    """Test search_papers_with_graph applies filter_arxiv_ids correctly."""
    mock_retriever.search = AsyncMock(return_value={
        "results": [
            {
                "arxiv_id": "2301.00001",
                "title": "Included Paper",
                "graph_metadata": {"citation_count": 10},
                "chunks": [],
            },
            {
                "arxiv_id": "2301.00002",
                "title": "Filtered Out",
                "graph_metadata": {"citation_count": 5},
                "chunks": [],
            },
        ],
        "graph_insights": {},
    })

    result = tools_module.search_papers_with_graph(
        query="test",
        filter_arxiv_ids=["2301.00001"],
    )

    assert len(result["results"]) == 1
    assert result["results"][0]["arxiv_id"] == "2301.00001"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["arxiv_id"] == "2301.00001"


@pytest.mark.asyncio
async def test_get_paper_details(mock_db_session, mock_neo4j_client, mock_retriever, tools_module):
    """Test get_paper_details tool."""
    mock_paper = Mock()
    mock_paper.arxiv_id = "2301.00001"
    mock_paper.title = "Test Paper"
    mock_paper.abstract = "Abstract"
    mock_paper.authors = ["Author A"]
    mock_paper.published_date = datetime(2023, 1, 1)
    mock_paper.primary_category = "cs.AI"
    mock_paper.categories = ["cs.AI"]

    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_paper

    mock_client = MagicMock()
    mock_neo4j_client.return_value.__enter__.return_value = mock_client
    mock_client.execute_query.return_value = [{"citation_count": 50, "is_seminal": False}]

    mock_retriever.vector_search = AsyncMock(return_value=[
        {"section_title": "Intro", "chunk_text": "Content"}
    ])

    tools_module.clear_tool_cache()

    result = tools_module.get_paper_details(arxiv_id="2301.00001")

    assert result["arxiv_id"] == "2301.00001"
    assert result["title"] == "Test Paper"
    assert result["citation_count"] == 50
    assert len(result["sample_content"]) == 1

    cached_results = tools_module.get_all_tool_results()
    assert len(cached_results) == 1
    assert cached_results[0]["tool_name"] == "get_paper_details"


@pytest.mark.asyncio
async def test_get_paper_details_not_found(mock_db_session, tools_module):
    """Test get_paper_details when paper is not found."""
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    result = tools_module.get_paper_details(arxiv_id="unknown")

    assert "error" in result
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_search_papers_fallback(mock_retriever, tools_module):
    """Test search_papers_with_graph fallback on error."""
    mock_retriever.search.side_effect = [Exception("Primary failed"), {"results": []}]

    result = tools_module.search_papers_with_graph(query="test")

    assert result.get("fallback") is True

    assert mock_retriever.search.call_count == 2


@pytest.mark.asyncio
async def test_search_papers_fallback_error(mock_retriever, tools_module):
    """Test search_papers_with_graph when both primary and fallback fail."""
    mock_retriever.search.side_effect = Exception("Total failure")

    result = tools_module.search_papers_with_graph(query="test")

    assert result.get("fallback") is True
    assert "error" in result
