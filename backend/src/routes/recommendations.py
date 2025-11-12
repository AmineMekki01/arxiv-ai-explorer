from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import provide_sync_session
from src.services.recommendations import PaperRecommender
from src.services.knowledge_graph import Neo4jClient
from src.models.user import User
from src.routes.auth import require_auth
from src.core import logger


router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


class TrackInteractionRequest(BaseModel):
    """Request to track a user interaction."""
    arxiv_id: str
    interaction_type: str
    paper_title: Optional[str] = None
    metadata: Optional[dict] = None


class RecommendationResponse(BaseModel):
    """Recommended paper."""
    arxiv_id: str
    title: str
    abstract: Optional[str]
    authors: List[str]
    published_date: Optional[str]
    categories: List[str]
    citation_count: int
    recommendation_score: float
    thumbnail_url: str
    reasons: List[str] = []


class UserStatsResponse(BaseModel):
    """User interaction statistics."""
    total_interactions: int
    papers_viewed: int
    papers_saved: int
    papers_liked: int
    preferred_categories: List[str]
    preferred_authors: List[str]
    first_interaction: Optional[str]
    last_interaction: Optional[str]


def get_auth_user_id(current_user: User = Depends(require_auth)) -> str:
    """Return authenticated user's UUID as string."""
    return str(current_user.id)


@router.get("", response_model=List[RecommendationResponse])
@router.get("/", response_model=List[RecommendationResponse])
async def get_recommendations(
    limit: int = 20,
    offset: int = 0,
    strategies: Optional[str] = None,
    user_id: str = Depends(get_auth_user_id),
    db: Session = Depends(provide_sync_session)
):
    """
    Get personalized paper recommendations for the user.
    
    Strategies:
    - content: Based on papers you've viewed (categories, authors)
    - citation: Based on citation networks
    - collaborative: Based on similar users
    - trending: Currently popular papers
    """
    try:
        strategy_list = None
        if strategies:
            raw_list = [s.strip().lower() for s in strategies.split(",") if s.strip()]
            normalized = []
            for s in raw_list:
                if s == "citation":
                    normalized.append("graph")
                elif s in {"content", "graph", "semantic", "trending", "collaborative"}:
                    normalized.append(s)
                else:
                    continue
            strategy_list = normalized
            logger.info(f"/api/recommendations resolved strategies: {strategy_list}")
        
        neo4j_client = None
        try:
            neo4j_client = Neo4jClient()
            neo4j_client.connect()
        except Exception as e:
            logger.warning(f"Neo4j not available for citation recommendations: {e}")
        
        recommender = PaperRecommender(db, neo4j_client)
        
        recommendations = recommender.get_recommendations(
            user_id=user_id,
            limit=limit,
            offset=offset,
            strategies=strategy_list
        )
        
        if neo4j_client:
            neo4j_client.close()
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))