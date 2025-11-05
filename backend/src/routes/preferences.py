from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from datetime import datetime

from src.database import get_sync_session
from src.models.user import User, UserPreferences
from src.routes.auth import require_auth
from src.core import logger

router = APIRouter(prefix="/preferences", tags=["preferences"])


class UserPreferencesResponse(BaseModel):
    id: str
    user_id: str
    preferred_categories: List[str]
    theme: str
    items_per_page: str
    email_notifications: bool
    default_search_limit: str
    default_context_strategy: str
    custom_settings: dict
    updated_at: datetime


class UpdatePreferencesRequest(BaseModel):
    preferred_categories: Optional[List[str]] = None
    theme: Optional[str] = Field(None, pattern="^(light|dark|auto)$")
    items_per_page: Optional[str] = None
    email_notifications: Optional[bool] = None
    default_search_limit: Optional[str] = None
    default_context_strategy: Optional[str] = None
    custom_settings: Optional[dict] = None


ARXIV_CATEGORIES = [
    "cs.AI",
    "cs.CL",
    "cs.CV",
    "cs.LG",
    "cs.NE",
    "cs.RO",
    "stat.ML",
    "math.OC",
    "eess.AS",
    "eess.IV",
    "q-bio",
    "physics",
]


@router.get("", response_model=UserPreferencesResponse)
async def get_preferences(current_user: User = Depends(require_auth)):
    """Get user preferences."""
    try:
        with get_sync_session() as db:
            prefs = db.query(UserPreferences).filter(
                UserPreferences.user_id == current_user.id
            ).first()
            
            if not prefs:
                prefs = UserPreferences(
                    user_id=current_user.id,
                    preferred_categories=[],
                    theme="light",
                    items_per_page="10",
                    email_notifications=True,
                    default_search_limit="10",
                    default_context_strategy="trimming",
                    custom_settings={},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(prefs)
                db.commit()
                db.refresh(prefs)
            
            return UserPreferencesResponse(
                id=str(prefs.id),
                user_id=str(prefs.user_id),
                preferred_categories=prefs.preferred_categories or [],
                theme=prefs.theme,
                items_per_page=prefs.items_per_page,
                email_notifications=prefs.email_notifications,
                default_search_limit=prefs.default_search_limit,
                default_context_strategy=prefs.default_context_strategy,
                custom_settings=prefs.custom_settings or {},
                updated_at=prefs.updated_at
            )
            
    except Exception as e:
        logger.error(f"Error fetching preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch preferences"
        )


@router.patch("", response_model=UserPreferencesResponse)
async def update_preferences(
    request: UpdatePreferencesRequest,
    current_user: User = Depends(require_auth)
):
    """Update user preferences."""
    try:
        with get_sync_session() as db:
            prefs = db.query(UserPreferences).filter(
                UserPreferences.user_id == current_user.id
            ).first()
            
            if not prefs:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Preferences not found"
                )
            
            if request.preferred_categories is not None:
                prefs.preferred_categories = request.preferred_categories
            if request.theme is not None:
                prefs.theme = request.theme
            if request.items_per_page is not None:
                prefs.items_per_page = request.items_per_page
            if request.email_notifications is not None:
                prefs.email_notifications = request.email_notifications
            if request.default_search_limit is not None:
                prefs.default_search_limit = request.default_search_limit
            if request.default_context_strategy is not None:
                prefs.default_context_strategy = request.default_context_strategy
            if request.custom_settings is not None:
                prefs.custom_settings = request.custom_settings
            
            prefs.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(prefs)
            
            logger.info(f"Updated preferences for user: {current_user.email}")
            
            return UserPreferencesResponse(
                id=str(prefs.id),
                user_id=str(prefs.user_id),
                preferred_categories=prefs.preferred_categories or [],
                theme=prefs.theme,
                items_per_page=prefs.items_per_page,
                email_notifications=prefs.email_notifications,
                default_search_limit=prefs.default_search_limit,
                default_context_strategy=prefs.default_context_strategy,
                custom_settings=prefs.custom_settings or {},
                updated_at=prefs.updated_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )


@router.get("/categories")
async def get_available_categories():
    """Get list of available arXiv categories."""
    return {
        "categories": [
            {"code": "cs.AI", "name": "Artificial Intelligence"},
            {"code": "cs.CL", "name": "Computation and Language (NLP)"},
            {"code": "cs.CV", "name": "Computer Vision and Pattern Recognition"},
            {"code": "cs.LG", "name": "Machine Learning"},
            {"code": "cs.NE", "name": "Neural and Evolutionary Computing"},
            {"code": "cs.RO", "name": "Robotics"},
            {"code": "stat.ML", "name": "Machine Learning (Statistics)"},
            {"code": "math.OC", "name": "Optimization and Control"},
            {"code": "eess.AS", "name": "Audio and Speech Processing"},
            {"code": "eess.IV", "name": "Image and Video Processing"},
            {"code": "q-bio", "name": "Quantitative Biology"},
            {"code": "physics", "name": "Physics"},
        ]
    }
