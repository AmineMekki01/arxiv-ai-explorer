import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone

from src.services.recommendations.recommender import PaperRecommender
from src.models.paper import Paper


@pytest.mark.unit
class TestPaperRecommender:
    """Tests for the PaperRecommender service."""
    
    def test_recommender_initialization(self, sync_session):
        """Test recommender initialization."""
        recommender = PaperRecommender(db=sync_session)
        
        assert recommender.db is not None
        assert recommender.neo4j_client is None
    
    def test_base_arxiv_id_normalization(self):
        """Test arXiv ID normalization."""
        assert PaperRecommender._base_arxiv_id("2301.00001v3") == "2301.00001"
        assert PaperRecommender._base_arxiv_id("2301.00001") == "2301.00001"
        assert PaperRecommender._base_arxiv_id(None) is None
        assert PaperRecommender._base_arxiv_id("1234.5678v1") == "1234.5678"
        assert PaperRecommender._base_arxiv_id("1234.5678v10") == "1234.5678"
    
    def test_interaction_weights(self):
        """Test interaction weight constants."""
        assert PaperRecommender.INTERACTION_WEIGHTS["saved"] == 5.0
        assert PaperRecommender.INTERACTION_WEIGHTS["liked"] == 3.0
        assert PaperRecommender.INTERACTION_WEIGHTS["viewed"] == 0.5
        assert PaperRecommender.PREFERENCE_WEIGHT == 10.0

    def test_get_user_interactions(self, sync_session):
        """Test retrieving user interactions."""
        recommender = PaperRecommender(db=sync_session)

        user_id = "test-user-id"
        interactions = recommender._get_user_interactions(user_id, days=90)

        assert "saved" in interactions
        assert "liked" in interactions
        assert "viewed" in interactions
        assert isinstance(interactions["saved"], list)
        assert isinstance(interactions["liked"], list)
        assert isinstance(interactions["viewed"], list)

    def test_cold_start_recommendations(self, sync_session):
        """Test recommendations for new users."""
        recommender = PaperRecommender(db=sync_session)

        recommendations = recommender._cold_start_recommendations(limit=10)
        assert isinstance(recommendations, list)

    def test_content_based_recommendations_no_data(self, sync_session):
        """Test content-based recommendations with no interaction data."""
        recommender = PaperRecommender(db=sync_session)

        interactions = {
            "saved": [],
            "liked": [],
            "viewed": [],
        }

        recommendations, reasons = recommender._content_based_recommendations(
            user_id="test-user",
            interactions=interactions,
        )

        assert isinstance(recommendations, dict)
        assert isinstance(reasons, dict)

    def test_merge_recommendations(self, sync_session):
        """Test merging recommendation scores."""
        recommender = PaperRecommender(db=sync_session)

        target = {"2301.00001": 0.5}
        source = {"2301.00001": 0.8, "2301.00002": 0.6}

        recommender._merge_recommendations(target, source, weight=2.0)

        assert "2301.00001" in target
        assert "2301.00002" in target
        assert target["2301.00001"] > 0.5
        assert target["2301.00002"] == 0.6 * 2.0

    def test_mmr_select_diversity(self, sync_session):
        """Test MMR selection for diversity."""
        recommender = PaperRecommender(db=sync_session)

        paper1 = Paper(
            arxiv_id="2301.00001",
            title="AI Paper 1",
            abstract="About AI",
            authors=["Author 1"],
            published_date=datetime.now(timezone.utc),
            arxiv_url="http://example.com/1",
            pdf_url="http://example.com/1.pdf",
            primary_category="cs.AI",
            categories=["cs.AI"],
        )

        paper2 = Paper(
            arxiv_id="2301.00002",
            title="CV Paper 1",
            abstract="About computer vision",
            authors=["Author 2"],
            published_date=datetime.now(timezone.utc),
            arxiv_url="http://example.com/2",
            pdf_url="http://example.com/2.pdf",
            primary_category="cs.CV",
            categories=["cs.CV"],
        )

        candidates = [
            ("2301.00001", 0.9),
            ("2301.00002", 0.85),
        ]

        paper_map = {
            "2301.00001": paper1,
            "2301.00002": paper2,
        }

        selected = recommender._mmr_select(
            candidates=candidates,
            paper_map=paper_map,
            k=2,
            lambda_=0.5,
        )

        assert len(selected) <= 2
        assert all(arxiv_id in paper_map for arxiv_id in selected)

    def test_graph_based_recommendations(self, sync_session):
        """Test graph-based recommendation strategy."""
        mock_neo4j_instance = MagicMock()
        mock_neo4j_instance.driver.session.return_value.__enter__.return_value.run.return_value = []

        recommender = PaperRecommender(db=sync_session, neo4j_client=mock_neo4j_instance)

        interactions = {
            "saved": [MagicMock(arxiv_id="2301.00001", created_at=datetime.now(timezone.utc))],
            "liked": [],
            "viewed": [],
        }

        recommendations, reasons = recommender._graph_based_recommendations(
            user_id="test-user",
            interactions=interactions,
        )

        assert isinstance(recommendations, dict)
        assert isinstance(reasons, dict)

    def test_get_recommendations_with_strategies(self, sync_session):
        """Test getting recommendations with specific strategies."""
        recommender = PaperRecommender(db=sync_session)

        recommendations = recommender.get_recommendations(
            user_id="new-user",
            limit=5,
            strategies=["cold_start"],
        )

        assert isinstance(recommendations, (dict, list))

    def test_content_based_recommendations_with_data_and_prefs(self, sync_session):
        """Content-based recommendations should score similar papers using interactions and prefs."""
        from src.models.paper_interaction import PaperLike

        recommender = PaperRecommender(db=sync_session)

        now = datetime.now(timezone.utc)
        base_paper = Paper(
            arxiv_id="2301.10001",
            title="Base AI Paper",
            abstract="About AI",
            authors=["Author A"],
            published_date=now,
            arxiv_url="http://example.com/base",
            pdf_url="http://example.com/base.pdf",
            primary_category="cs.AI",
            categories=["cs.AI", "cs.LG"],
            citation_count=5,
        )
        similar_paper = Paper(
            arxiv_id="2301.10002",
            title="Similar AI Paper",
            abstract="More AI",
            authors=["Author A"],
            published_date=now,
            arxiv_url="http://example.com/sim",
            pdf_url="http://example.com/sim.pdf",
            primary_category="cs.AI",
            categories=["cs.AI"],
            citation_count=2,
        )
        sync_session.add_all([base_paper, similar_paper])
        sync_session.commit()

        like = PaperLike(
            user_id="user-1",
            arxiv_id=base_paper.arxiv_id,
            paper_title=base_paper.title,
        )
        sync_session.add(like)
        sync_session.commit()

        class Prefs:
            preferred_categories = ["cs.AI"]

        interactions = {"saved": [], "liked": [like], "viewed": []}

        recommendations, reasons = recommender._content_based_recommendations(
            user_id="user-1",
            interactions=interactions,
            user_prefs=Prefs(),
        )

        assert isinstance(recommendations, dict)
        assert similar_paper.arxiv_id in recommendations
        assert recommendations[similar_paper.arxiv_id] > 0.0
        assert isinstance(reasons, dict)

    def test_map_graph_id_to_db_exact_and_version_fallback(self, sync_session):
        """_map_graph_id_to_db should handle exact and versioned arxiv_ids."""
        recommender = PaperRecommender(db=sync_session)

        now = datetime.now(timezone.utc)
        exact = Paper(
            arxiv_id="2301.20001v2",
            title="Exact Version",
            abstract="",
            authors=["Author"],
            published_date=now,
            arxiv_url="http://e/2",
            pdf_url="http://e/2.pdf",
            primary_category="cs.AI",
            categories=["cs.AI"],
            citation_count=1,
        )
        newer = Paper(
            arxiv_id="2301.20001v3",
            title="Newer Version",
            abstract="",
            authors=["Author"],
            published_date=now + timedelta(days=1),
            arxiv_url="http://e/3",
            pdf_url="http://e/3.pdf",
            primary_category="cs.AI",
            categories=["cs.AI"],
            citation_count=2,
        )
        sync_session.add_all([exact, newer])
        sync_session.commit()

        mapped_exact = recommender._map_graph_id_to_db("2301.20001v2")
        assert mapped_exact == "2301.20001v2"

        mapped_latest = recommender._map_graph_id_to_db("2301.20001v999")
        assert mapped_latest == "2301.20001v3"

        assert recommender._map_graph_id_to_db("") is None

    def test_graph_based_recommendations_with_results(self, sync_session):
        """Graph-based recommendations should accumulate scores and reasons for related papers."""
        from src.models.paper_interaction import PaperView

        mock_neo4j_instance = MagicMock()
        run_mock = mock_neo4j_instance.driver.session.return_value.__enter__.return_value.run
        run_mock.side_effect = [
            [{"arxiv_id": "2301.30002", "citation_count": 5}],
            [{"arxiv_id": "2301.30003", "citation_count": 2}],
            [{"arxiv_id": "2301.30004", "citation_count": 1}],
        ]

        recommender = PaperRecommender(db=sync_session, neo4j_client=mock_neo4j_instance)
        recommender._map_graph_id_to_db = lambda rid: rid

        now = datetime.now(timezone.utc)
        interactions = {
            "saved": [],
            "liked": [],
            "viewed": [
                PaperView(
                    user_id="u1",
                    arxiv_id="2301.30001",
                    referrer=None,
                    duration_seconds=10,
                    created_at=now,
                )
            ],
        }

        recommendations, reasons = recommender._graph_based_recommendations(
            user_id="u1",
            interactions=interactions,
        )

        for aid in ["2301.30002", "2301.30003", "2301.30004"]:
            assert aid in recommendations
            assert recommendations[aid] > 0.0
            assert isinstance(reasons.get(aid, []), list)

    def test_get_recommendations_trending_strategy(self, sync_session):
        """When 'trending' is requested, recommender should delegate to cold-start even with interactions."""
        from src.models.paper_interaction import PaperLike

        recommender = PaperRecommender(db=sync_session)
        now = datetime.now(timezone.utc)
        paper = Paper(
            arxiv_id="2301.40001",
            title="Trending Paper",
            abstract="",
            authors=["Author"],
            published_date=now,
            arxiv_url="http://t/1",
            pdf_url="http://t/1.pdf",
            primary_category="cs.AI",
            categories=["cs.AI"],
            citation_count=20,
        )
        sync_session.add(paper)
        sync_session.commit()

        like = PaperLike(user_id="user-t", arxiv_id=paper.arxiv_id, paper_title=paper.title)
        sync_session.add(like)
        sync_session.commit()

        recommendations = recommender.get_recommendations(
            user_id="user-t",
            limit=5,
            strategies=["trending"],
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) <= 5

    def test_get_recommendations_fallback_when_no_scores(self, sync_session, monkeypatch):
        """Fallback path should recommend papers in top categories when semantic/content give no scores."""
        from src.models.paper_interaction import PaperLike

        now = datetime.now(timezone.utc)
        recommender = PaperRecommender(db=sync_session)

        interacted = Paper(
            arxiv_id="2301.50001",
            title="Interacted",
            abstract="",
            authors=["Author"],
            published_date=now - timedelta(days=10),
            arxiv_url="http://i/1",
            pdf_url="http://i/1.pdf",
            primary_category="cs.AI",
            categories=["cs.AI"],
            citation_count=5,
        )
        candidate = Paper(
            arxiv_id="2301.50002",
            title="Candidate",
            abstract="",
            authors=["Other"],
            published_date=now - timedelta(days=5),
            arxiv_url="http://i/2",
            pdf_url="http://i/2.pdf",
            primary_category="cs.AI",
            categories=["cs.AI"],
            citation_count=3,
        )
        sync_session.add_all([interacted, candidate])
        sync_session.commit()

        like = PaperLike(user_id="user-f", arxiv_id=interacted.arxiv_id, paper_title=interacted.title)
        sync_session.add(like)
        sync_session.commit()

        def fake_semantic(self, user_id, interactions, seeds_limit=5, per_seed=30):
            return {}, {}

        def fake_content(self, user_id, interactions, user_prefs=None):
            return {}, {}

        monkeypatch.setattr(PaperRecommender, "_semantic_recommendations", fake_semantic)
        monkeypatch.setattr(PaperRecommender, "_content_based_recommendations", fake_content)

        recommendations = recommender.get_recommendations(
            user_id="user-f",
            limit=5,
            strategies=["semantic", "content"],
        )

        assert isinstance(recommendations, list)
        ids = [r["arxiv_id"] for r in recommendations]
        assert candidate.arxiv_id in ids
        assert interacted.arxiv_id not in ids
