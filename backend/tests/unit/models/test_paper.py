import pytest
from datetime import datetime, timezone
from src.models.paper import Paper


@pytest.mark.unit
class TestPaperModel:
    """Tests for the Paper model."""
    
    def test_paper_creation(self, sample_paper_data):
        """Test creating a paper with valid data."""
        paper = Paper(**sample_paper_data)
        
        assert paper.arxiv_id == "2301.00001"
        assert paper.title == "Test Paper: A Novel Approach"
        assert paper.abstract == "This is a test paper abstract."
        assert len(paper.authors) == 2
        assert paper.primary_category == "cs.AI"
        assert paper.citation_count == 10
    
    def test_paper_short_title(self, sample_paper_data):
        """Test short_title property."""
        paper = Paper(**sample_paper_data)
        assert paper.short_title == sample_paper_data["title"]
        
        long_title = "A" * 150
        paper.title = long_title
        assert len(paper.short_title) == 103
        assert paper.short_title.endswith("...")
    
    def test_paper_author_names(self, sample_paper_data):
        """Test author_names property formatting."""
        paper = Paper(**{**sample_paper_data, "authors": ["John Doe"]})
        assert paper.author_names == "John Doe"
        
        paper.authors = ["John Doe", "Jane Smith"]
        assert paper.author_names == "John Doe, Jane Smith"
        
        paper.authors = ["John Doe", "Jane Smith", "Bob Johnson"]
        assert paper.author_names == "John Doe, Jane Smith, Bob Johnson"
        
        paper.authors = ["John Doe", "Jane Smith", "Bob Johnson", "Alice Williams"]
        assert paper.author_names == "John Doe et al."
        
        paper.authors = []
        assert paper.author_names == "Unknown"
    
    def test_paper_has_citation_data(self, sample_paper_data):
        """Test has_citation_data property."""
        paper = Paper(**sample_paper_data)
        
        paper.references = None
        paper.cited_by = None
        assert not paper.has_citation_data
        
        paper.references = [{"arxiv_id": "2301.00002"}]
        assert paper.has_citation_data
        
        paper.references = None
        paper.cited_by = [{"arxiv_id": "2301.00003"}]
        assert paper.has_citation_data
    
    def test_paper_citation_velocity(self, sample_paper_data):
        """Test citation_velocity calculation."""
        paper = Paper(**sample_paper_data)
        
        paper.published_date = datetime.now(timezone.utc)
        paper.citation_count = 100
        velocity = paper.citation_velocity
        assert velocity > 0
        
        paper.citation_count = 0
        assert paper.citation_velocity == 0.0
        
        paper.published_date = None
        assert paper.citation_velocity == 0.0
    
    @pytest.mark.asyncio
    async def test_paper_persistence(self, async_session, sample_paper_data):
        """Test saving and retrieving paper from database."""
        paper = Paper(**sample_paper_data)
        async_session.add(paper)
        await async_session.commit()
        await async_session.refresh(paper)
        
        assert paper.id is not None
        assert paper.arxiv_id == "2301.00001"
    
    @pytest.mark.asyncio
    async def test_paper_unique_arxiv_id(self, async_session, sample_paper_data):
        """Test that arxiv_id must be unique."""
        from sqlalchemy.exc import IntegrityError
        
        paper1 = Paper(**sample_paper_data)
        async_session.add(paper1)
        await async_session.commit()
        
        paper2 = Paper(**sample_paper_data)
        async_session.add(paper2)
        
        with pytest.raises(IntegrityError):
            await async_session.commit()
    
    def test_paper_repr(self, sample_paper_data):
        """Test __repr__ method."""
        paper = Paper(**sample_paper_data)
        paper.id = 1
        
        repr_str = repr(paper)
        assert "Paper" in repr_str
        assert "2301.00001" in repr_str
        assert "Test Paper" in repr_str
