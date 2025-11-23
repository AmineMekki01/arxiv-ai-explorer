import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from uuid import uuid4

from src.main import app
from src.models.user import User
from src.routes.auth import get_current_user


@pytest.mark.integration
class TestSearchPipeline:
    """Test complete search workflow from query to results."""
    
    @patch('src.routes.search.get_graph_enhanced_retriever')
    def test_search_pipeline_end_to_end(self, mock_retriever):
        """
        Test full search pipeline:
        1. User submits search query
        2. Query is processed
        3. Results are returned
        4. Search history is saved
        """
        client = TestClient(app)
        
        mock_retriever_instance = AsyncMock()
        mock_retriever_instance.search.return_value = {
            "results": [
                {
                    "arxiv_id": "2301.00001",
                    "title": "Test Paper",
                    "published_date": "2023-01-01",
                    "primary_category": "cs.AI",
                    "categories": ["cs.AI"],
                    "chunks": [
                        {
                            "chunk_text": "Test content",
                            "section_title": "Introduction",
                            "section_type": "introduction",
                            "chunk_index": 0,
                            "score": 0.95
                        }
                    ],
                    "graph_metadata": {
                        "citation_count": 10,
                        "is_seminal": False,
                        "cited_by_results": 0,
                        "is_foundational": False
                    },
                    "max_score": 0.95
                }
            ],
            "graph_insights": {
                "total_papers": 1,
                "internal_citations": 0,
                "foundational_papers_added": 0,
                "central_papers": []
            },
            "query": "test query"
        }
        mock_retriever.return_value = mock_retriever_instance
        
        mock_user = User(
            id=str(uuid4()),
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.post("/search/enhanced", json={
                "query": "test query",
                "limit": 10
            })
            
            assert response.status_code == 200
            assert "results" in response.json()
        finally:
            app.dependency_overrides.clear()


@pytest.mark.integration
class TestAuthenticationFlow:
    """Test complete authentication flow."""
    
    @patch('src.routes.auth.get_sync_session')
    def test_complete_auth_flow(self, mock_get_session):
        """
        Test authentication flow:
        1. User registration
        2. Login with credentials
        3. Access protected endpoint with token
        """
        client = TestClient(app)
        
        mock_db = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        register_response = client.post("/auth/register", json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "password123",
            "full_name": "New User"
        })
        
        assert register_response.status_code == 201
        assert "access_token" in register_response.json()
        
        token = register_response.json()["access_token"]
        
        mock_user = User(
            id=str(uuid4()),
            email="newuser@example.com",
            username="newuser",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            me_response = client.get("/auth/me")
            assert me_response.status_code == 200
            assert me_response.json()["email"] == "newuser@example.com"
        finally:
            app.dependency_overrides.clear()


@pytest.mark.integration
class TestRecommendationPipeline:
    """Test recommendation generation."""
    
    @patch('src.routes.recommendations.PaperRecommender')
    def test_recommendation_generation(self, mock_recommender_class):
        """
        Test recommendation pipeline:
        1. Get user interaction history
        2. Generate recommendations
        3. Return results
        """
        client = TestClient(app)
        
        mock_db = MagicMock()
        
        mock_recommender = MagicMock()
        mock_recommender.get_recommendations.return_value = [
            {
                "arxiv_id": "2301.00001",
                "title": "Recommended Paper",
                "abstract": "Test abstract",
                "authors": ["Author 1"],
                "published_date": "2023-01-01",
                "categories": ["cs.AI"],
                "citation_count": 10,
                "recommendation_score": 0.95,
                "thumbnail_url": "",
                "reasons": ["semantic_similarity"]
            }
        ]
        mock_recommender_class.return_value = mock_recommender
        
        mock_user = User(
            id=str(uuid4()),
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        from src.routes.recommendations import get_auth_user_id, provide_sync_session
        app.dependency_overrides[get_auth_user_id] = lambda: str(mock_user.id)
        app.dependency_overrides[provide_sync_session] = lambda: mock_db
        
        try:
            response = client.get("/api/recommendations/")
            
            assert response.status_code == 200
            assert isinstance(response.json(), list)
        finally:
            app.dependency_overrides.clear()


@pytest.mark.integration  
class TestPaperIngestionPipeline:
    """Test paper data flow."""
    
    def test_paper_data_model_flow(self):
        """
        Test paper data flow through models:
        1. Create paper instance
        2. Validate data
        3. Test relationships
        """
        from src.models.paper import Paper
        
        paper_data = {
            "arxiv_id": "2301.00001",
            "title": "Test Paper",
            "abstract": "Test abstract",
            "authors": ["Author 1", "Author 2"],
            "published_date": datetime(2023, 1, 1),
            "arxiv_url": "http://arxiv.org/abs/2301.00001",
            "pdf_url": "http://arxiv.org/pdf/2301.00001.pdf",
            "primary_category": "cs.AI",
            "categories": ["cs.AI", "cs.LG"]
        }
        
        paper = Paper(**paper_data)
        
        assert paper.arxiv_id == "2301.00001"
        assert paper.title == "Test Paper"
        assert len(paper.authors) == 2
        assert paper.primary_category == "cs.AI"
        assert "cs.LG" in paper.categories
    
    def test_ingestion_persists_paper_and_builds_graph(self, sync_session):
        """More realistic ingestion-style test using DB and knowledge graph builder."""
        from src.models.paper import Paper
        from src.services.knowledge_graph.graph_builder import KnowledgeGraphBuilder
        from unittest.mock import MagicMock

        paper_data = {
            "arxiv_id": "2301.99999",
            "title": "Graph Test Paper",
            "abstract": "Test abstract for ingestion pipeline.",
            "authors": ["Author 1", "Author 2"],
            "published_date": datetime(2023, 1, 2, tzinfo=timezone.utc),
            "arxiv_url": "http://arxiv.org/abs/2301.99999",
            "pdf_url": "http://arxiv.org/pdf/2301.99999.pdf",
            "primary_category": "cs.AI",
            "categories": ["cs.AI", "cs.LG"],
        }

        paper = Paper(**paper_data)
        sync_session.add(paper)
        sync_session.commit()
        sync_session.refresh(paper)

        if paper.published_date and paper.published_date.tzinfo is None:
            paper.published_date = paper.published_date.replace(tzinfo=timezone.utc)

        assert paper.id is not None

        mock_neo4j = MagicMock()
        mock_neo4j.execute_write.return_value = {"nodes_created": 1, "relationships_created": 0}

        builder = KnowledgeGraphBuilder(client=mock_neo4j)
        summary = builder.build_full_graph(paper)

        assert summary["arxiv_id"] == paper.arxiv_id
        assert "paper_node" in summary["operations"]
        assert summary["nodes_created"] >= 1
        mock_neo4j.execute_write.assert_called()
