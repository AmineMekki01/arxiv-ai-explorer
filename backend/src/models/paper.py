from sqlalchemy import Column, String, Text, JSON, DateTime, Integer, Float, Index, Boolean

from src.database import Base


class Paper(Base):
    """Model for storing arXiv papers and their metadata."""
    
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    arxiv_id = Column(String(50), unique=True, index=True, nullable=False)
    arxiv_url = Column(String(500), nullable=False)
    pdf_url = Column(String(500), nullable=False)
    
    title = Column(Text, nullable=False, index=True)
    abstract = Column(Text, nullable=False)
    authors = Column(JSON, nullable=False)
    
    published_date = Column(DateTime(timezone=True), nullable=False)
    updated_date = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    primary_category = Column(String(50), nullable=False, index=True)
    categories = Column(JSON, nullable=False)
    subjects = Column(JSON, nullable=True)
    
    full_text = Column(Text, nullable=True)
    key_concepts = Column(JSON, nullable=True)
    methodology = Column(Text, nullable=True)
    contributions = Column(JSON, nullable=True)
    limitations = Column(JSON, nullable=True)
    
    citation_count = Column(Integer, default=0, nullable=False)
    references = Column(JSON, nullable=True)
    cited_by = Column(JSON, nullable=True)
    
    embedding_vector = Column(Text, nullable=True)
    embedding_model = Column(String(100), nullable=True)
    
    quality_score = Column(Float, nullable=True)
    relevance_scores = Column(JSON, nullable=True)
    
    is_processed = Column(Boolean, default=False, nullable=False)
    is_embedded = Column(Boolean, default=False, nullable=False)
    processing_errors = Column(JSON, nullable=True)
    
    local_pdf_path = Column(String(500), nullable=True)
    local_text_path = Column(String(500), nullable=True)
    
    download_count = Column(Integer, default=0, nullable=False)
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<Paper(id={self.id}, arxiv_id='{self.arxiv_id}', title='{self.title[:50]}...')>"
    
    @property
    def short_title(self) -> str:
        """Return a shortened version of the title."""
        return self.title[:100] + "..." if len(self.title) > 100 else self.title
    
    @property
    def author_names(self) -> str:
        """Return formatted author names."""
        if not self.authors:
            return "Unknown"
        if len(self.authors) == 1:
            return self.authors[0]
        elif len(self.authors) <= 3:
            return ", ".join(self.authors)
        else:
            return f"{self.authors[0]} et al."

    __table_args__ = (
        Index('idx_papers_category_date', 'primary_category', 'published_date'),
        Index('idx_papers_processed', 'is_processed', 'is_embedded'),
    )
