"""API endpoints for Knowledge Graph queries."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from src.services.knowledge_graph import Neo4jClient, GraphQueryService
from src.models.graph_models import (
    PaperNode, SimilarPaper, InfluentialPaper,
    CitationNetwork, ResearchPath,
    Collaborator,
    TrendingConcept
)
from src.core import logger

router = APIRouter(prefix="/graph", tags=["knowledge-graph"])


@router.get("/papers/{arxiv_id}/similar", response_model=List[SimilarPaper])
async def get_similar_papers(
    arxiv_id: str,
    method: str = Query("concept", regex="^(concept|author|citation|combined)$"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Find papers similar to the given paper.
    
    **Methods:**
    - `concept`: Papers sharing research concepts
    - `author`: Papers by same authors
    - `citation`: Papers sharing citations
    - `combined`: Weighted combination of all methods
    """
    try:
        with Neo4jClient() as client:
            service = GraphQueryService(client)
            results = service.find_similar_papers(arxiv_id, limit, method)
            
            return [SimilarPaper(**r) for r in results]
            
    except Exception as e:
        logger.error(f"Failed to find similar papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/papers/{arxiv_id}/citation-network", response_model=CitationNetwork)
async def get_citation_network(
    arxiv_id: str,
    depth: int = Query(2, ge=1, le=3)
):
    """
    Get citation network around a paper.
    
    Returns papers this paper cites and papers that cite it,
    up to the specified depth.
    """
    try:
        with Neo4jClient() as client:
            service = GraphQueryService(client)
            
            
            result = service.find_citation_network(arxiv_id, depth)
            
            if not result:
                return CitationNetwork(
                    center_paper=arxiv_id,
                    cited_papers=[],
                    citing_papers=[],
                    depth=depth
                )

            cited_raw = result.get("cited_papers", [])
            citing_raw = result.get("citing_papers", [])
            
            def to_external_url(item: dict) -> str:
                aid = item.get("arxiv_id")
                doi = item.get("doi")
                s2 = item.get("s2_paper_id")
                if aid:
                    return f"https://arxiv.org/abs/{aid}"
                if doi:
                    return f"https://doi.org/{doi}"
                if s2:
                    return f"https://www.semanticscholar.org/paper/{s2}"
                return ""

            cited = []
            for p in cited_raw:
                if p is None:
                    continue
                if isinstance(p, dict):
                    p["external_url"] = to_external_url(p)
                    cited.append(PaperNode(**p))
                else:
                    cited.append(PaperNode(
                        arxiv_id=p.get('arxiv_id'),
                        s2_paper_id=p.get('s2_paper_id'),
                        doi=p.get('doi'),
                        title=p.get('title'),
                        citation_count=p.get('citation_count'),
                        is_seminal=p.get('is_highly_cited', False),
                        external_url=to_external_url(p)
                    ))
            
            citing = []
            for p in citing_raw:
                if p is None:
                    continue
                if isinstance(p, dict):
                    p["external_url"] = to_external_url(p)
                    citing.append(PaperNode(**p))
                else:
                    citing.append(PaperNode(
                        arxiv_id=p.get('arxiv_id'),
                        s2_paper_id=p.get('s2_paper_id'),
                        doi=p.get('doi'),
                        title=p.get('title'),
                        citation_count=p.get('citation_count'),
                        is_seminal=p.get('is_highly_cited', False),
                        external_url=to_external_url(p)
                    ))

            logger.info(f"Returning {len(cited)} cited papers and {len(citing)} citing papers")
            return CitationNetwork(
                center_paper=arxiv_id,
                cited_papers=cited,
                citing_papers=citing,
                depth=depth
            )
            
    except Exception as e:
        msg = str(e)
        logger.warning(f"Citation network lookup fallback for {arxiv_id}: {msg}")
        try:
            return CitationNetwork(
                center_paper=arxiv_id,
                cited_papers=[],
                citing_papers=[],
                depth=depth
            )
        except Exception:
            logger.error(f"Failed to get citation network: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/papers/path", response_model=ResearchPath)
async def find_research_path(
    from_arxiv_id: str = Query(..., description="Starting paper arXiv ID"),
    to_arxiv_id: str = Query(..., description="Target paper arXiv ID"),
    max_hops: int = Query(5, ge=1, le=10)
):
    """
    Find shortest citation path between two papers.
    
    Shows how papers are connected through citation network,
    useful for tracing research lineage.
    """
    try:
        with Neo4jClient() as client:
            service = GraphQueryService(client)
            path = service.find_research_path(from_arxiv_id, to_arxiv_id, max_hops)
            
            if not path:
                raise HTTPException(
                    status_code=404,
                    detail=f"No path found between {from_arxiv_id} and {to_arxiv_id}"
                )
            
            return ResearchPath(
                from_paper=from_arxiv_id,
                to_paper=to_arxiv_id,
                path=[PaperNode(**p) for p in path],
                length=len(path) - 1
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find research path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/papers/influential", response_model=List[InfluentialPaper])
async def get_influential_papers(
    category: Optional[str] = Query(None, description="Filter by arXiv category"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Find most influential papers by citation count.
    
    Can optionally filter by arXiv category (e.g., cs.AI, cs.CL).
    """
    try:
        with Neo4jClient() as client:
            service = GraphQueryService(client)
            results = service.find_influential_papers(category, limit)
            
            return [InfluentialPaper(**r) for r in results]
            
    except Exception as e:
        logger.error(f"Failed to find influential papers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/concepts/trending", response_model=List[TrendingConcept])
async def get_trending_concepts(
    time_window_days: int = Query(180, ge=30, le=730),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Find trending research concepts.
    
    Identifies concepts appearing most frequently in recent papers.
    """
    try:
        with Neo4jClient() as client:
            service = GraphQueryService(client)
            results = service.find_trending_concepts(time_window_days, limit)
            
            return [TrendingConcept(**r) for r in results]
            
    except Exception as e:
        logger.error(f"Failed to find trending concepts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/authors/{author_name}/collaborations", response_model=List[Collaborator])
async def get_author_collaborations(
    author_name: str,
    limit: int = Query(10, ge=1, le=50)
):
    """
    Find collaboration network for an author.
    
    Shows who the author has published with and how many shared papers.
    """
    try:
        with Neo4jClient() as client:
            service = GraphQueryService(client)
            results = service.find_author_collaborations(author_name, limit)
            
            return [Collaborator(**r) for r in results]
            
    except Exception as e:
        logger.error(f"Failed to find collaborations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/concepts/gaps")
async def find_research_gaps(
    concept1: str = Query(..., description="First research concept"),
    concept2: str = Query(..., description="Second research concept")
):
    """
    Find papers bridging two research concepts.
    
    Useful for identifying interdisciplinary work or research gaps.
    """
    try:
        with Neo4jClient() as client:
            service = GraphQueryService(client)
            results = service.find_research_gaps(concept1, concept2)
            
            return {
                "concept1": concept1,
                "concept2": concept2,
                "bridging_papers": [PaperNode(**r) for r in results]
            }
            
    except Exception as e:
        logger.error(f"Failed to find research gaps: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/papers/{arxiv_id}/context")
async def get_paper_context(arxiv_id: str):
    """
    Get comprehensive context for a paper.
    
    Returns all nodes and relationships connected to this paper:
    authors, concepts, institutions, citations, etc.
    """
    try:
        with Neo4jClient() as client:
            service = GraphQueryService(client)
            context = service.get_paper_context(arxiv_id)
            
            if not context:
                raise HTTPException(
                    status_code=404,
                    detail=f"Paper {arxiv_id} not found in knowledge graph"
                )
            
            return context
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get paper context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

