from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field

from src.database import get_sync_session
from src.models.user import User
from src.models.bookmark import Bookmark
from src.models.paper import Paper
from src.routes.auth import require_auth

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


class BookmarkCreateRequest(BaseModel):
    arxiv_id: str = Field(..., min_length=5, max_length=50)
    title: Optional[str] = None


class BookmarkResponse(BaseModel):
    id: str
    arxiv_id: str
    title: Optional[str]
    paper_id: Optional[int]


@router.get("", response_model=List[BookmarkResponse])
async def list_bookmarks(current_user: User = Depends(require_auth)):
    try:
        with get_sync_session() as db:
            rows = (
                db.query(Bookmark)
                .filter(Bookmark.user_id == current_user.id)
                .order_by(Bookmark.created_at.desc())
                .all()
            )
            return [
                BookmarkResponse(
                    id=str(b.id), arxiv_id=b.arxiv_id, title=b.title, paper_id=b.paper_id
                )
                for b in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list bookmarks: {e}")


@router.post("", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
async def add_bookmark(request: BookmarkCreateRequest, current_user: User = Depends(require_auth)):
    try:
        with get_sync_session() as db:
            paper = db.query(Paper).filter(Paper.arxiv_id == request.arxiv_id).first()
            bm = (
                db.query(Bookmark)
                .filter(Bookmark.user_id == current_user.id, Bookmark.arxiv_id == request.arxiv_id)
                .first()
            )
            if bm:
                return BookmarkResponse(
                    id=str(bm.id), arxiv_id=bm.arxiv_id, title=bm.title, paper_id=bm.paper_id
                )
            bm = Bookmark(
                user_id=current_user.id,
                arxiv_id=request.arxiv_id,
                paper_id=paper.id if paper else None,
                title=request.title or (paper.title[:512] if paper and paper.title else None),
            )
            db.add(bm)
            db.commit()
            db.refresh(bm)
            return BookmarkResponse(
                id=str(bm.id), arxiv_id=bm.arxiv_id, title=bm.title, paper_id=bm.paper_id
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add bookmark: {e}")


@router.delete("")
async def remove_bookmark(
    arxiv_id: Optional[str] = Query(default=None),
    id: Optional[str] = Query(default=None),
    current_user: User = Depends(require_auth),
):
    if not arxiv_id and not id:
        raise HTTPException(status_code=400, detail="Specify arxiv_id or id")
    try:
        with get_sync_session() as db:
            q = db.query(Bookmark).filter(Bookmark.user_id == current_user.id)
            if arxiv_id:
                q = q.filter(Bookmark.arxiv_id == arxiv_id)
            if id:
                q = q.filter(Bookmark.id == id)
            deleted = 0
            for row in q.all():
                db.delete(row)
                deleted += 1
            db.commit()
            if deleted == 0:
                raise HTTPException(status_code=404, detail="Bookmark not found")
            return {"status": "success", "deleted": deleted}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove bookmark: {e}")
