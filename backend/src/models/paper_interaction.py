from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.database import Base


class PaperSave(Base):
    """User saves/bookmarks a paper."""
    
    __tablename__ = "paper_saves"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(String, nullable=False, index=True)
    
    arxiv_id = Column(String, nullable=False, index=True)
    paper_title = Column(String)
    
    notes = Column(String)
    folder = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'arxiv_id', name='unique_user_paper_save'),
    )
    
    def __repr__(self):
        return f"<PaperSave {self.user_id} -> {self.arxiv_id}>"


class PaperLike(Base):
    """User likes a paper."""
    
    __tablename__ = "paper_likes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(String, nullable=False, index=True)
    arxiv_id = Column(String, nullable=False, index=True)
    paper_title = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'arxiv_id', name='unique_user_paper_like'),
    )
    
    def __repr__(self):
        return f"<PaperLike {self.user_id} -> {self.arxiv_id}>"


class PaperView(Base):
    """Track paper views (simple analytics)."""
    
    __tablename__ = "paper_views"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(String, nullable=False, index=True)
    
    arxiv_id = Column(String, nullable=False, index=True)
    
    referrer = Column(String)
    duration_seconds = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<PaperView {self.user_id} -> {self.arxiv_id}>"
