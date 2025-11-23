import pytest
from uuid import uuid4
from datetime import datetime, timezone

from src.services.interactions.paper_interactions import PaperInteractionService
from src.models.user import User
from src.models.paper import Paper


@pytest.mark.unit
class TestPaperInteractionService:
    """Tests for PaperInteractionService."""
    
    @pytest.fixture
    def service(self, sync_session):
        return PaperInteractionService(sync_session)
    
    @pytest.fixture
    def user(self, sync_session):
        user = User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        sync_session.add(user)
        sync_session.commit()
        return user
    
    @pytest.fixture
    def paper(self, sync_session):
        paper = Paper(
            arxiv_id="2301.00001",
            title="Test Paper",
            abstract="Abstract",
            authors=["Author A"],
            published_date=datetime.now(timezone.utc),
            updated_date=datetime.now(timezone.utc),
            primary_category="cs.AI",
            categories=["cs.AI"],
            arxiv_url="http://arxiv.org/abs/2301.00001",
            pdf_url="http://arxiv.org/pdf/2301.00001.pdf"
        )
        sync_session.add(paper)
        sync_session.commit()
        return paper
    
    def test_save_paper(self, service, user, paper):
        """Test saving a paper."""
        result = service.save_paper(
            user_id=str(user.id),
            arxiv_id=paper.arxiv_id,
            paper_title=paper.title,
            notes="My notes",
            folder="My Folder"
        )
        
        assert result["status"] == "created"
        assert result["save"]["arxiv_id"] == paper.arxiv_id
        assert result["save"]["notes"] == "My notes"
        
        assert service.is_saved(str(user.id), paper.arxiv_id)
    
    def test_save_paper_already_saved(self, service, user, paper):
        """Test saving an already saved paper (update)."""
        service.save_paper(str(user.id), paper.arxiv_id, notes="Old notes")
        
        result = service.save_paper(
            user_id=str(user.id),
            arxiv_id=paper.arxiv_id,
            notes="New notes"
        )
        
        assert result["status"] == "already_saved"
        assert result["save"]["notes"] == "New notes"
    
    def test_unsave_paper(self, service, user, paper):
        """Test unsaving a paper."""
        service.save_paper(str(user.id), paper.arxiv_id)
        
        result = service.unsave_paper(str(user.id), paper.arxiv_id)
        assert result is True
        assert not service.is_saved(str(user.id), paper.arxiv_id)
    
    def test_get_saved_papers(self, service, user, paper):
        """Test getting saved papers."""
        service.save_paper(str(user.id), paper.arxiv_id)
        
        papers = service.get_saved_papers(str(user.id))
        assert len(papers) == 1
        assert papers[0]["arxiv_id"] == paper.arxiv_id
        assert papers[0]["title"] == paper.title
    
    def test_like_paper(self, service, user, paper):
        """Test liking a paper."""
        result = service.like_paper(str(user.id), paper.arxiv_id, paper.title)
        
        assert result["status"] == "created"
        assert service.is_liked(str(user.id), paper.arxiv_id)
        assert service.get_like_count(paper.arxiv_id) == 1
    
    def test_unlike_paper(self, service, user, paper):
        """Test unliking a paper."""
        service.like_paper(str(user.id), paper.arxiv_id)
        
        result = service.unlike_paper(str(user.id), paper.arxiv_id)
        assert result is True
        assert not service.is_liked(str(user.id), paper.arxiv_id)
    
    def test_get_liked_papers(self, service, user, paper):
        """Test getting liked papers."""
        service.like_paper(str(user.id), paper.arxiv_id)
        
        papers = service.get_liked_papers(str(user.id))
        assert len(papers) == 1
        assert papers[0]["arxiv_id"] == paper.arxiv_id
    
    def test_track_view(self, service, user, paper):
        """Test tracking a view."""
        service.track_view(str(user.id), paper.arxiv_id, referrer="search", duration_seconds=60)
        
        assert service.get_view_count(paper.arxiv_id) == 1
    
    def test_get_paper_stats(self, service, user, paper):
        """Test getting paper stats."""
        service.save_paper(str(user.id), paper.arxiv_id)
        service.like_paper(str(user.id), paper.arxiv_id)
        service.track_view(str(user.id), paper.arxiv_id)
        
        stats = service.get_paper_stats(paper.arxiv_id, str(user.id))
        
        assert stats["likes"] == 1
        assert stats["views_total"] == 1
        assert stats["saves"] == 1
        assert stats["user_saved"] is True
        assert stats["user_liked"] is True
    
    def test_get_user_stats(self, service, user, paper):
        """Test getting user stats."""
        service.save_paper(str(user.id), paper.arxiv_id)
        service.like_paper(str(user.id), paper.arxiv_id)
        service.track_view(str(user.id), paper.arxiv_id)
        
        stats = service.get_user_stats(str(user.id))
        
        assert stats["saves_count"] == 1
        assert stats["likes_count"] == 1
        assert stats["views_count"] == 1
