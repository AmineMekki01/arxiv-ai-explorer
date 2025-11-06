from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.database import get_sync_session
from src.models.user import User
from src.models.search_history import SearchHistory
from src.routes.auth import require_auth

router = APIRouter(prefix="/history", tags=["history"])


class SearchHistoryItem(BaseModel):
    id: str
    query: str
    params: Optional[dict] = None
    results_count: Optional[str] = None
    created_at: str


@router.get("", response_model=List[SearchHistoryItem])
async def list_history(limit: int = Query(25, ge=1, le=200), current_user: User = Depends(require_auth)):
    """Return recent search history for the authenticated user."""
    try:
        with get_sync_session() as db:
            rows = (
                db.query(SearchHistory)
                .filter(SearchHistory.user_id == current_user.id)
                .order_by(SearchHistory.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                SearchHistoryItem(
                    id=str(r.id),
                    query=r.query,
                    params=r.params,
                    results_count=r.results_count,
                    created_at=r.created_at.isoformat() if r.created_at else ""
                )
                for r in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list history: {e}")


@router.delete("")
async def clear_history(current_user: User = Depends(require_auth)):
    """Clear all search history for the user."""
    try:
        with get_sync_session() as db:
            rows = (
                db.query(SearchHistory)
                .filter(SearchHistory.user_id == current_user.id)
                .all()
            )
            deleted = 0
            for r in rows:
                db.delete(r)
                deleted += 1
            db.commit()
            return {"status": "success", "deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {e}")
