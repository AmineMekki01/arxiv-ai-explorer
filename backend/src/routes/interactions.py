from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import provide_sync_session
from src.services.interactions import PaperInteractionService
from src.routes.auth import require_auth
from src.models.user import User
from src.models.paper import Paper
from src.core import logger

router = APIRouter(prefix="/api/papers", tags=["interactions"])

class SavePaperRequest(BaseModel):
    """Request to save a paper."""
    arxiv_id: str
    paper_title: Optional[str] = None
    notes: Optional[str] = None
    folder: Optional[str] = None


class LikePaperRequest(BaseModel):
    """Request to like a paper."""
    arxiv_id: str
    paper_title: Optional[str] = None


class TrackViewRequest(BaseModel):
    """Request to track a view."""
    arxiv_id: str
    paper_title: Optional[str] = None
    referrer: Optional[str] = None
    duration_seconds: Optional[int] = None


class SavedPaperResponse(BaseModel):
    """Saved paper with details."""
    save_id: str
    arxiv_id: str
    title: str
    abstract: Optional[str]
    authors: List[str]
    published_date: Optional[str]
    categories: List[str]
    citation_count: int
    saved_at: str
    notes: Optional[str]
    folder: Optional[str]


class PaperStatsResponse(BaseModel):
    """Paper interaction statistics."""
    arxiv_id: str
    likes: int
    views_total: int
    views_7d: int
    saves: int
    user_saved: Optional[bool] = None
    user_liked: Optional[bool] = None


class UserStatsResponse(BaseModel):
    """User interaction statistics."""
    views_count: int
    likes_count: int
    saves_count: int
    interactions_count: int
    preferred_categories: List[str] = []
    preferred_authors: List[str] = []

def get_auth_user_id(current_user: User = Depends(require_auth)) -> str:
    """Return authenticated user's UUID as string."""
    return str(current_user.id)


@router.post("/save")
async def save_paper(
    request: SavePaperRequest,
    user_id: str = Depends(get_auth_user_id),
    db: Session = Depends(provide_sync_session)
):
    """
    Save/bookmark a paper.
    
    Returns the save object. If already saved, updates notes/folder.
    """
    try:
        service = PaperInteractionService(db)
        result = service.save_paper(
            user_id=user_id,
            arxiv_id=request.arxiv_id,
            paper_title=request.paper_title,
            notes=request.notes,
            folder=request.folder
        )
        return result
        
    except Exception as e:
        logger.error(f"Error saving paper: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/save/{arxiv_id}")
async def unsave_paper(
    arxiv_id: str,
    user_id: str = Depends(get_auth_user_id),
    db: Session = Depends(provide_sync_session)
):
    """Remove a saved paper."""
    try:
        service = PaperInteractionService(db)
        removed = service.unsave_paper(user_id, arxiv_id)
        
        if removed:
            return {"status": "success", "message": "Paper unsaved"}
        else:
            raise HTTPException(status_code=404, detail="Save not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsaving paper: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/save", response_model=List[SavedPaperResponse])
async def get_saved_papers(
    folder: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_auth_user_id),
    db: Session = Depends(provide_sync_session)
):
    """
    Get user's saved papers.
    
    Optionally filter by folder.
    """
    try:
        service = PaperInteractionService(db)
        saves = service.get_saved_papers(
            user_id=user_id,
            folder=folder,
            limit=limit,
            offset=offset
        )
        return saves
        
    except Exception as e:
        logger.error(f"Error getting saved papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/save/{arxiv_id}/check")
async def check_if_saved(
    arxiv_id: str,
    user_id: str = Depends(get_auth_user_id),
    db: Session = Depends(provide_sync_session)
):
    """Check if user has saved this paper."""
    try:
        service = PaperInteractionService(db)
        is_saved = service.is_saved(user_id, arxiv_id)
        return {"arxiv_id": arxiv_id, "is_saved": is_saved}
        
    except Exception as e:
        logger.error(f"Error checking save status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/like")
async def get_liked_papers(
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_auth_user_id),
    db: Session = Depends(provide_sync_session)
):
    """
    Get user's liked papers.
    """
    try:
        service = PaperInteractionService(db)
        likes = service.get_liked_papers(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        return likes
        
    except Exception as e:
        logger.error(f"Error getting liked papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/like")
async def like_paper(
    request: LikePaperRequest,
    user_id: str = Depends(get_auth_user_id),
    db: Session = Depends(provide_sync_session)
):
    """Like a paper."""
    try:
        service = PaperInteractionService(db)
        result = service.like_paper(
            user_id=user_id,
            arxiv_id=request.arxiv_id,
            paper_title=request.paper_title
        )
        return result
        
    except Exception as e:
        logger.error(f"Error liking paper: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/like/{arxiv_id}")
async def unlike_paper(
    arxiv_id: str,
    user_id: str = Depends(get_auth_user_id),
    db: Session = Depends(provide_sync_session)
):
    """Remove a like."""
    try:
        service = PaperInteractionService(db)
        removed = service.unlike_paper(user_id, arxiv_id)
        
        if removed:
            return {"status": "success", "message": "Paper unliked"}
        else:
            raise HTTPException(status_code=404, detail="Like not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unliking paper: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/like/{arxiv_id}/check")
async def check_if_liked(
    arxiv_id: str,
    user_id: str = Depends(get_auth_user_id),
    db: Session = Depends(provide_sync_session)
):
    """Check if user has liked this paper."""
    try:
        service = PaperInteractionService(db)
        is_liked = service.is_liked(user_id, arxiv_id)
        return {"arxiv_id": arxiv_id, "is_liked": is_liked}
        
    except Exception as e:
        logger.error(f"Error checking like status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/view")
async def track_view(
    request: TrackViewRequest,
    user_id: str = Depends(get_auth_user_id),
    db: Session = Depends(provide_sync_session)
):
    """Track a paper view (for analytics)."""
    try:
        print("Tracking view for paper:", request.arxiv_id)
        print("User ID:", user_id)
        service = PaperInteractionService(db)
        service.track_view(
            user_id=user_id,
            arxiv_id=request.arxiv_id,
            referrer=request.referrer,
            duration_seconds=request.duration_seconds
        )
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error tracking view: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/{arxiv_id}/stats", response_model=PaperStatsResponse)
async def get_paper_stats(
    arxiv_id: str,
    user_id: Optional[str] = Depends(get_auth_user_id),
    db: Session = Depends(provide_sync_session)
):
    """
    Get interaction statistics for a paper.
    
    Includes likes, views, saves.
    If user_id provided, also includes user's interaction status.
    """
    try:
        service = PaperInteractionService(db)
        stats = service.get_paper_stats(arxiv_id, user_id)
        return stats
        
    except Exception as e:
        logger.error(f"Error getting paper stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: str = Depends(get_auth_user_id),
    db: Session = Depends(provide_sync_session)
):
    """Get user's interaction statistics."""
    print("get_user_stats")
    logger.info(f"user_id : {user_id}")
    print("user_id : ", user_id)
    try:
        from sqlalchemy import func
        from src.models.paper_interaction import PaperSave, PaperLike, PaperView

        saves_count = db.query(func.count(PaperSave.id)).filter(PaperSave.user_id == user_id).scalar() or 0
        likes_count = db.query(func.count(PaperLike.id)).filter(PaperLike.user_id == user_id).scalar() or 0
        views_count = db.query(func.count(PaperView.id)).filter(PaperView.user_id == user_id).scalar() or 0
        interactions_count = int(saves_count) + int(likes_count) + int(views_count)

        user_views = db.query(PaperView).filter(PaperView.user_id == user_id).all()
        viewed_arxiv_ids = [v.arxiv_id for v in user_views]
        authors_rows = []
        if viewed_arxiv_ids:
            authors_rows = db.query(Paper.authors, Paper.categories).filter(Paper.arxiv_id.in_(viewed_arxiv_ids)).all()
        
        authors_set = set()
        categories_set = set()
        for row in authors_rows:
            authors_list = None
            categories_list = None
            if isinstance(row, tuple) and len(row) > 0:
                authors_list = row[0]
                categories_list = row[1]
            elif hasattr(row, "authors"):
                authors_list = getattr(row, "authors", None)
                categories_list = getattr(row, "categories", None)
            if isinstance(authors_list, list):
                for a in authors_list:
                    if isinstance(a, str) and a:
                        authors_set.add(a)
            if isinstance(categories_list, list):
                for c in categories_list:
                    if isinstance(c, str) and c:
                        categories_set.add(c)
        preferred_authors = list(authors_set)
        preferred_categories = list(categories_set)

        stats = {
            "saves_count": saves_count,
            "likes_count": likes_count,
            "views_count": views_count,
            "interactions_count": interactions_count,
            "preferred_categories": preferred_categories,
            "preferred_authors": preferred_authors
        }

        return stats
        
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
