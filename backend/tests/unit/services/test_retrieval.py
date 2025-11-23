import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.services.retrieval.graph_enhanced_retriever import GraphEnhancedRetriever


@pytest.mark.unit
class TestGraphEnhancedRetriever:
    """Tests for the GraphEnhancedRetriever service."""
    
    @patch('src.services.retrieval.graph_enhanced_retriever.Neo4jClient')
    @patch('src.services.retrieval.graph_enhanced_retriever.AsyncQdrantClient')
    @patch('src.services.retrieval.graph_enhanced_retriever.get_shared_embedder')
    def test_retriever_initialization(self, mock_embedder, mock_qdrant, mock_neo4j):
        """Test retriever initialization."""
        retriever = GraphEnhancedRetriever()
        
        assert retriever is not None
        assert retriever._embedder is not None
        assert retriever.qdrant is not None
    
    @pytest.mark.asyncio
    @patch('src.services.retrieval.graph_enhanced_retriever.AsyncQdrantClient')
    @patch('src.services.retrieval.graph_enhanced_retriever.get_shared_embedder')
    async def test_vector_search_basic(self, mock_embedder_fn, mock_qdrant_cls):
        """Test basic vector search functionality."""
        mock_dense = MagicMock()
        mock_dense.tolist.return_value = [0.1] * 384
        
        mock_sparse = MagicMock()
        mock_sparse.as_object.return_value = {
            "indices": [1, 2],
            "values": [0.5, 0.3]
        }
        
        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = {
            "dense": mock_dense,
            "sparse": mock_sparse
        }
        mock_embedder_fn.return_value = mock_embedder
        
        mock_qdrant = AsyncMock()
        mock_point = MagicMock()
        mock_point.id = "chunk_1"
        mock_point.score = 0.95
        mock_point.payload = {
            "arxiv_id": "2301.00001",
            "chunk_text": "Test chunk",
            "section_title": "Introduction",
            "title": "Test Paper"
        }
        mock_qdrant.query_points.return_value = MagicMock(points=[mock_point])
        mock_qdrant_cls.return_value = mock_qdrant
        
        retriever = GraphEnhancedRetriever()
        results = await retriever.vector_search("test query", limit=10)
        
        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0]["arxiv_id"] == "2301.00001"
    
    @pytest.mark.asyncio
    @patch('src.services.retrieval.graph_enhanced_retriever.AsyncQdrantClient')
    @patch('src.services.retrieval.graph_enhanced_retriever.get_shared_embedder')
    async def test_vector_search_with_filters(self, mock_embedder_fn, mock_qdrant_cls):
        """Test vector search with arxiv_id filters."""
        mock_dense = MagicMock()
        mock_dense.tolist.return_value = [0.1] * 384
        
        mock_sparse = MagicMock()
        mock_sparse.as_object.return_value = {
            "indices": [1],
            "values": [0.5]
        }
        
        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = {
            "dense": mock_dense,
            "sparse": mock_sparse
        }
        mock_embedder_fn.return_value = mock_embedder
        
        mock_qdrant = AsyncMock()
        mock_qdrant.query_points.return_value = MagicMock(points=[])
        mock_qdrant_cls.return_value = mock_qdrant
        
        retriever = GraphEnhancedRetriever()
        results = await retriever.vector_search(
            "test query",
            limit=10,
            filter_arxiv_ids=["2301.00001", "2301.00002"]
        )
        
        assert isinstance(results, list)
    
    def test_rerank_with_graph(self):
        """Test graph-based reranking."""
        retriever = GraphEnhancedRetriever()
        
        chunks = [
            {
                "arxiv_id": "2301.00001",
                "score": 0.9,
                "chunk_text": "Test",
                "published_date": "2023-01-01"
            },
            {
                "arxiv_id": "2301.00002",
                "score": 0.8,
                "chunk_text": "Test2",
                "published_date": "2023-01-02"
            }
        ]
        
        graph_insights = {
            "papers_metadata": {
                "2301.00001": {"is_seminal": True, "citation_count": 150},
                "2301.00002": {"is_seminal": False, "citation_count": 50}
            },
            "internal_citations": []
        }
        
        reranked = retriever._rerank_with_graph(chunks, graph_insights, "test query")
        
        assert len(reranked) == 2
        assert reranked[0]["arxiv_id"] == "2301.00001"
        assert reranked[0]["final_score"] > chunks[0]["score"]
    
    def test_smart_select_diversity(self):
        """Test smart diversity selection."""
        retriever = GraphEnhancedRetriever()
        
        chunks = [
            {"arxiv_id": "2301.00001", "score": 0.9, "final_score": 0.9, "graph_metadata": {}},
            {"arxiv_id": "2301.00001", "score": 0.85, "final_score": 0.85, "graph_metadata": {}},
            {"arxiv_id": "2301.00002", "score": 0.8, "final_score": 0.8, "graph_metadata": {}},
            {"arxiv_id": "2301.00003", "score": 0.75, "final_score": 0.75, "graph_metadata": {}},
        ]
        
        selected = retriever._smart_select(chunks, limit=3)
        
        assert len(selected) <= 3
        assert isinstance(selected, list)
        unique_papers = set(c["arxiv_id"] for c in selected)
        assert len(unique_papers) <= 3
    
    def test_identify_central_papers(self):
        """Test identification of central papers in citation network."""
        retriever = GraphEnhancedRetriever()
        
        internal_citations = [
            {"source": "2301.00001", "target": "2301.00999"},
            {"source": "2301.00002", "target": "2301.00999"},
            {"source": "2301.00003", "target": "2301.00999"},
        ]
        
        central_papers = retriever._identify_central_papers(internal_citations)
        
        assert "2301.00999" in central_papers
    
    def test_group_chunks_by_paper(self):
        """Test grouping chunks by paper."""
        retriever = GraphEnhancedRetriever()
        
        chunks = [
            {
                "arxiv_id": "2301.00001",
                "title": "Paper 1",
                "chunk_text": "Chunk 1",
                "final_score": 0.9,
                "section_title": "Introduction",
                "graph_metadata": {}
            },
            {
                "arxiv_id": "2301.00001",
                "title": "Paper 1",
                "chunk_text": "Chunk 2",
                "final_score": 0.85,
                "section_title": "Methods",
                "graph_metadata": {}
            },
            {
                "arxiv_id": "2301.00002",
                "title": "Paper 2",
                "chunk_text": "Chunk 3",
                "final_score": 0.80,
                "section_title": "Results",
                "graph_metadata": {}
            }
        ]
        
        graph_insights = {}
        
        grouped = retriever._group_chunks_by_paper(chunks, graph_insights)
        
        assert len(grouped) == 2
        assert len(grouped[0]["chunks"]) == 2
        assert grouped[0]["max_score"] >= grouped[1]["max_score"]

    @pytest.mark.asyncio
    async def test_search_no_chunks_returns_empty(self):
        """search should return empty structure when vector_search yields no chunks."""
        retriever = GraphEnhancedRetriever()

        async def fake_vector_search(*args, **kwargs):
            return []

        retriever.vector_search = fake_vector_search

        result = await retriever.search("no results query", limit=5)

        assert result["results"] == []
        assert result["graph_insights"] == {}
        assert result["query"] == "no results query"

    @pytest.mark.asyncio
    async def test_search_with_foundations_and_graph_insights(self):
        """search should integrate graph insights and foundation chunks when available."""
        retriever = GraphEnhancedRetriever()

        async def fake_vector_search(*args, **kwargs):
            return [
                {
                    "arxiv_id": "2301.00001",
                    "title": "Paper 1",
                    "chunk_text": "Chunk",
                    "score": 0.9,
                    "primary_category": "cs.AI",
                    "categories": ["cs.AI"],
                    "published_date": "2023-01-01",
                }
            ]

        async def fake_analyze_with_graph(paper_ids):
            return {
                "internal_citations": [{"source": "a", "target": "2301.00001"}],
                "missing_foundations": [
                    {"arxiv_id": "2301.99999", "total_citations": 10, "cited_by_results": 1}
                ],
                "papers_metadata": {
                    "2301.00001": {"citation_count": 5, "is_seminal": False}
                },
            }

        def fake_rerank_with_graph(chunks, graph_insights, query):
            for c in chunks:
                c["final_score"] = c.get("score", 0.0)
                c["graph_metadata"] = {
                    "citation_count": graph_insights["papers_metadata"].get(c["arxiv_id"], {}).get("citation_count", 0),
                    "is_seminal": False,
                    "cited_by_results": 0,
                    "is_foundational": False,
                }
            return chunks

        async def fake_fetch_foundation_chunks(foundations, original_query):
            return [
                {
                    "type": "chunk",
                    "arxiv_id": "2301.99999",
                    "title": "Foundation",
                    "chunk_text": "Foundation chunk",
                    "primary_category": "cs.AI",
                    "categories": ["cs.AI"],
                    "published_date": "2020-01-01",
                    "score": 1.0,
                    "source": "foundation",
                    "graph_metadata": {
                        "citation_count": 10,
                        "is_seminal": True,
                        "cited_by_results": 1,
                        "is_foundational": True,
                    },
                    "final_score": 1.5,
                }
            ]

        def fake_smart_select(chunks, limit):
            return chunks[:limit]

        retriever.vector_search = fake_vector_search
        retriever._analyze_with_graph = fake_analyze_with_graph
        retriever._rerank_with_graph = fake_rerank_with_graph
        retriever._fetch_foundation_chunks = fake_fetch_foundation_chunks
        retriever._smart_select = fake_smart_select

        result = await retriever.search("test query", limit=2, include_foundations=True)

        assert isinstance(result["results"], list)
        assert len(result["results"]) == 2
        assert result["graph_insights"]["total_papers"] == 1
        assert result["graph_insights"]["internal_citations"] == 1
        assert result["graph_insights"]["foundational_papers_added"] == 1

    @pytest.mark.asyncio
    async def test_analyze_with_graph_error_returns_empty(self, monkeypatch):
        """_analyze_with_graph should catch exceptions and return empty dict."""
        retriever = GraphEnhancedRetriever()

        class FailingClient:
            def __enter__(self):
                raise RuntimeError("boom")

            def __exit__(self, exc_type, exc, tb):
                return False

        monkeypatch.setattr(
            "src.services.retrieval.graph_enhanced_retriever.Neo4jClient",
            lambda *args, **kwargs: FailingClient(),
        )

        insights = await retriever._analyze_with_graph(["2301.00001"])
        assert insights == {}

    @pytest.mark.asyncio
    @patch("src.services.retrieval.graph_enhanced_retriever.AsyncQdrantClient")
    @patch("src.services.embeddings.multi_vector_embedder.MultiVectorEmbedder")
    async def test_fetch_foundation_chunks_error_handled(self, mock_embedder_cls, mock_qdrant_cls):
        """_fetch_foundation_chunks should handle errors and continue gracefully."""
        retriever = GraphEnhancedRetriever()

        mock_embedder = MagicMock()
        mock_embedder.embed_query.side_effect = RuntimeError("embed error")
        mock_embedder_cls.return_value = mock_embedder

        chunks = await retriever._fetch_foundation_chunks(
            foundations=[{"arxiv_id": "2301.00001"}],
            original_query="test query",
        )

        assert chunks == []
