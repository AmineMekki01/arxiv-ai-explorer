from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.services.retrieval.graph_enhanced_retriever import get_graph_enhanced_retriever
from src.core import logger

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    """Search request payload."""
    query: str = Field(..., description="Search query", min_length=1)
    limit: int = Field(10, description="Number of results to return", ge=1, le=50)
    include_foundations: bool = Field(
        True,
        description="Include foundational papers discovered by graph"
    )
    min_foundation_citations: int = Field(
        3,
        description="Minimum citations for foundation detection",
        ge=1
    )


class ChunkResult(BaseModel):
    """Individual chunk from a paper."""
    chunk_text: str
    section_title: Optional[str] = None
    section_type: Optional[str] = None
    chunk_index: Optional[int] = None
    score: Optional[float] = None


class GraphMetadata(BaseModel):
    """Graph-derived metadata for a paper."""
    citation_count: int = 0
    is_seminal: bool = False
    cited_by_results: int = 0
    is_foundational: bool = False


class PaperResult(BaseModel):
    """Paper result with chunks and metadata."""
    arxiv_id: str
    title: str
    published_date: Optional[str] = None
    primary_category: Optional[str] = None
    categories: List[str] = []
    chunks: List[ChunkResult]
    graph_metadata: GraphMetadata
    max_score: float


class GraphInsights(BaseModel):
    """Insights from graph analysis."""
    total_papers: int
    internal_citations: int
    foundational_papers_added: int
    central_papers: List[str]


class SearchResponse(BaseModel):
    """Search response with results and insights."""
    results: List[PaperResult]
    graph_insights: GraphInsights
    query: str


@router.post("/enhanced", response_model=SearchResponse)
async def enhanced_search(request: SearchRequest):
    """
    Perform graph-enhanced search.
    
    This endpoint combines traditional hybrid search (dense + sparse embeddings)
    with graph intelligence from Neo4j to provide smarter results:
    
    - **Re-ranking**: Boosts seminal papers and papers cited by other results
    - **Foundation Discovery**: Adds frequently-cited papers missing from initial results
    - **Context Awareness**: Uses citation relationships for better ranking
    
    Example:
    ```json
    {
        "query": "transformer efficiency recent advances",
        "limit": 10,
        "include_foundations": true
    }
    ```
    """
    try:
        logger.info(f"Enhanced search request: {request.query} (limit={request.limit})")
        
        retriever = get_graph_enhanced_retriever()
        results = await retriever.search(
            query=request.query,
            limit=request.limit,
            include_foundations=request.include_foundations,
            min_foundation_citations=request.min_foundation_citations
        )
        
        logger.info(f"Enhanced search completed: {len(results['results'])} papers")
        return results
        
    except Exception as e:
        logger.error(f"Enhanced search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/enhanced", response_model=SearchResponse)
async def enhanced_search_get(
    query: str = Query(..., description="Search query", min_length=1),
    limit: int = Query(10, description="Number of results", ge=1, le=50),
    include_foundations: bool = Query(True, description="Include foundational papers")
):
    """
    Perform graph-enhanced search (GET version).
    
    Same as POST endpoint but accessible via GET for simple queries.
    """
    request = SearchRequest(
        query=query,
        limit=limit,
        include_foundations=include_foundations
    )
    return await enhanced_search(request)
