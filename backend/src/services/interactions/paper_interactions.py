from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, desc
from sqlalchemy.orm import Session

from src.models.paper_interaction import PaperSave, PaperLike, PaperView
from src.models.paper import Paper
from src.core import logger


class PaperInteractionService:
    """Manage user interactions with papers."""
    
    def __init__(self, db: Session):
        self.db = db
        
    def save_paper(
        self,
        user_id: str,
        arxiv_id: str,
        paper_title: Optional[str] = None,
        notes: Optional[str] = None,
        folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save/bookmark a paper.
        
        Returns:
            {"status": "created"|"already_saved", "save": PaperSave}
        """
        try:
            existing = self.db.query(PaperSave).filter(
                and_(
                    PaperSave.user_id == user_id,
                    PaperSave.arxiv_id == arxiv_id
                )
            ).first()
            
            if existing:
                if notes is not None:
                    existing.notes = notes
                if folder is not None:
                    existing.folder = folder
                self.db.commit()
                
                return {
                    "status": "already_saved",
                    "save": {
                        "id": str(existing.id),
                        "arxiv_id": existing.arxiv_id,
                        "created_at": existing.created_at.isoformat(),
                        "notes": existing.notes,
                        "folder": existing.folder
                    }
                }
            
            save = PaperSave(
                user_id=user_id,
                arxiv_id=arxiv_id,
                paper_title=paper_title,
                notes=notes,
                folder=folder
            )
            
            self.db.add(save)
            self.db.commit()
            
            logger.info(f"User {user_id} saved paper {arxiv_id}")
            
            return {
                "status": "created",
                "save": {
                    "id": str(save.id),
                    "arxiv_id": save.arxiv_id,
                    "created_at": save.created_at.isoformat(),
                    "notes": save.notes,
                    "folder": save.folder
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving paper: {e}")
            raise
    
    def unsave_paper(self, user_id: str, arxiv_id: str) -> bool:
        """
        Remove a saved paper.
        
        Returns:
            True if removed, False if not found
        """
        try:
            result = self.db.query(PaperSave).filter(
                and_(
                    PaperSave.user_id == user_id,
                    PaperSave.arxiv_id == arxiv_id
                )
            ).delete()
            
            self.db.commit()
            
            if result > 0:
                logger.info(f"User {user_id} unsaved paper {arxiv_id}")
                return True
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error unsaving paper: {e}")
            raise
    
    def get_saved_papers(
        self,
        user_id: str,
        folder: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's saved papers with full paper details."""
        query = self.db.query(PaperSave, Paper).join(
            Paper, PaperSave.arxiv_id == Paper.arxiv_id
        ).filter(PaperSave.user_id == user_id)
        
        if folder:
            query = query.filter(PaperSave.folder == folder)
        
        query = query.order_by(desc(PaperSave.created_at))
        results = query.limit(limit).offset(offset).all()
        
        saved_papers = []
        for save, paper in results:
            saved_papers.append({
                "save_id": str(save.id),
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "published_date": paper.published_date.isoformat() if paper.published_date else None,
                "categories": paper.categories,
                "citation_count": paper.citation_count,
                "saved_at": save.created_at.isoformat(),
                "notes": save.notes,
                "folder": save.folder
            })
        
        return saved_papers
    
    def is_saved(self, user_id: str, arxiv_id: str) -> bool:
        """Check if user has saved this paper."""
        return self.db.query(PaperSave).filter(
            and_(
                PaperSave.user_id == user_id,
                PaperSave.arxiv_id == arxiv_id
            )
        ).first() is not None
    
    def like_paper(
        self,
        user_id: str,
        arxiv_id: str,
        paper_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Like a paper.
        
        Returns:
            {"status": "created"|"already_liked", "like": PaperLike}
        """
        try:
            existing = self.db.query(PaperLike).filter(
                and_(
                    PaperLike.user_id == user_id,
                    PaperLike.arxiv_id == arxiv_id
                )
            ).first()
            
            if existing:
                return {
                    "status": "already_liked",
                    "like": {
                        "id": str(existing.id),
                        "arxiv_id": existing.arxiv_id,
                        "created_at": existing.created_at.isoformat()
                    }
                }
            
            like = PaperLike(
                user_id=user_id,
                arxiv_id=arxiv_id,
                paper_title=paper_title
            )
            
            self.db.add(like)
            self.db.commit()
            
            logger.info(f"User {user_id} liked paper {arxiv_id}")
            
            return {
                "status": "created",
                "like": {
                    "id": str(like.id),
                    "arxiv_id": like.arxiv_id,
                    "created_at": like.created_at.isoformat()
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error liking paper: {e}")
            raise
    
    def unlike_paper(self, user_id: str, arxiv_id: str) -> bool:
        """
        Remove a like.
        
        Returns:
            True if removed, False if not found
        """
        try:
            result = self.db.query(PaperLike).filter(
                and_(
                    PaperLike.user_id == user_id,
                    PaperLike.arxiv_id == arxiv_id
                )
            ).delete()
            
            self.db.commit()
            
            if result > 0:
                logger.info(f"User {user_id} unliked paper {arxiv_id}")
                return True
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error unliking paper: {e}")
            raise

    def get_liked_papers(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get user's liked papers with full paper details."""
        query = self.db.query(PaperLike, Paper).join(
            Paper, PaperLike.arxiv_id == Paper.arxiv_id
        ).filter(PaperLike.user_id == user_id)
        
        query = query.order_by(desc(PaperLike.created_at))
        results = query.limit(limit).offset(offset).all()
        
        liked_papers = []
        for like, paper in results:
            liked_papers.append({
                "like_id": str(like.id),
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "published_date": paper.published_date.isoformat() if paper.published_date else None,
                "categories": paper.categories,
                "citation_count": paper.citation_count,
                "liked_at": like.created_at.isoformat()
            })
        
        return liked_papers
    
    def is_liked(self, user_id: str, arxiv_id: str) -> bool:
        """Check if user has liked this paper."""
        return self.db.query(PaperLike).filter(
            and_(
                PaperLike.user_id == user_id,
                PaperLike.arxiv_id == arxiv_id
            )
        ).first() is not None
    
    def get_like_count(self, arxiv_id: str) -> int:
        """Get total likes for a paper."""
        return self.db.query(func.count(PaperLike.id)).filter(
            PaperLike.arxiv_id == arxiv_id
        ).scalar() or 0
    
    def track_view(
        self,
        user_id: str,
        arxiv_id: str,
        referrer: Optional[str] = None,
        duration_seconds: Optional[int] = None
    ):
        """Track a paper view."""
        try:
            view = PaperView(
                user_id=user_id,
                arxiv_id=arxiv_id,
                referrer=referrer,
                duration_seconds=duration_seconds
            )
            
            self.db.add(view)
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error tracking view: {e}")
    
    def get_view_count(self, arxiv_id: str, days: Optional[int] = None) -> int:
        """Get view count for a paper."""
        query = self.db.query(func.count(PaperView.id)).filter(
            PaperView.arxiv_id == arxiv_id
        )
        
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            query = query.filter(PaperView.created_at >= since)
        
        return query.scalar() or 0
    
    
    def get_paper_stats(self, arxiv_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all interaction stats for a paper."""
        stats = {
            "arxiv_id": arxiv_id,
            "likes": self.get_like_count(arxiv_id),
            "views_total": self.get_view_count(arxiv_id),
            "views_7d": self.get_view_count(arxiv_id, days=7),
            "saves": self.db.query(func.count(PaperSave.id)).filter(
                PaperSave.arxiv_id == arxiv_id
            ).scalar() or 0
        }
        
        if user_id:
            stats["user_saved"] = self.is_saved(user_id, arxiv_id)
            stats["user_liked"] = self.is_liked(user_id, arxiv_id)
        
        return stats
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user's interaction statistics."""
        return {
            "saves_count": self.db.query(func.count(PaperSave.id)).filter(
                PaperSave.user_id == user_id
            ).scalar() or 0,
            "likes_count": self.db.query(func.count(PaperLike.id)).filter(
                PaperLike.user_id == user_id
            ).scalar() or 0,
            "views_count": self.db.query(func.count(PaperView.id)).filter(
                PaperView.user_id == user_id
            ).scalar() or 0
        }
