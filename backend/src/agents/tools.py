from typing import Any, Dict, List, Optional
import asyncio
from loguru import logger
from datetime import datetime

from src.services.retrieval.graph_enhanced_retriever import GraphEnhancedRetriever
from agents import function_tool

graph_retriever = GraphEnhancedRetriever()

_last_tool_result: Optional[Dict[str, Any]] = None
_last_tool_timestamp: Optional[datetime] = None
_last_focused_papers = None
_tool_results: List[Dict[str, Any]] = []

def get_last_tool_result() -> Optional[Dict[str, Any]]:
    """Return the most recent tool result (for backwards compatibility)."""
    return _last_tool_result

def get_all_tool_results() -> List[Dict[str, Any]]:
    """Return all tool results captured for the current run/message."""
    return list(_tool_results)

def clear_tool_cache() -> None:
    """Clear cached tool results for the current run/message."""
    global _last_tool_result, _last_tool_timestamp, _last_focused_papers, _tool_results
    _last_tool_result = None
    _last_tool_timestamp = None
    _last_focused_papers = None
    _tool_results = []
    logger.info("Cleared tool cache")

def _update_tool_cache(tool_result: Dict[str, Any]) -> None:
    """Update cache with a new tool result, keeping both last and full history."""
    global _last_tool_result, _last_tool_timestamp, _tool_results
    _last_tool_result = tool_result
    _last_tool_timestamp = datetime.now()
    _tool_results.append(tool_result)
    sources = tool_result.get("sources") or []
    logger.info(
        f"Cached tool result for {tool_result.get('tool_name', 'unknown')} "
        f"with {len(sources)} sources"
    )

@function_tool
def search_papers_with_graph(
    query: str,
    limit: int = 10,
    include_foundations: bool = True,
    filter_arxiv_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    🚀 RECOMMENDED: Advanced graph-enhanced search combining vector similarity with citation network analysis.
    
    This tool provides superior results by:
    - Finding papers through semantic similarity (like regular search)
    - Analyzing citation networks to discover influential/foundational papers
    - Ranking results using citation counts and network centrality
    - Identifying relationships between papers
    - Discovering important papers that cite or are cited by your results
    
    Use this tool for:
    - Research questions about topics, methods, or concepts
    - Finding important/influential papers in a field
    - Exploring state-of-the-art research
    - Getting comprehensive coverage of a research area
    - Any query where you want the BEST results
    
    Returns detailed metadata including:
    - Paper titles, abstracts, and content
    - Citation counts (for identifying seminal works)
    - Graph badges (seminal, foundational, central papers)
    - Relationships between papers
    - Discovery insights (e.g., "Found 2 foundational papers cited by these results")
    
    Args:
        query: The search query (research topic, concept, method, etc.)
        limit: Number of results to return (default: 10)
        include_foundations: Whether to discover foundational papers (default: True, RECOMMENDED)
        filter_arxiv_ids: Optional list of arXiv IDs to filter results (for focused mode)
        
    Returns:
        Dictionary with:
        - results: List of papers with rich metadata
        - sources: Detailed source information for citations
        - graph_insights: Citation analysis, foundational discoveries
    
    Example queries:
    - "attention mechanisms in transformers"
    - "recent advances in diffusion models"
    - "seminal papers on reinforcement learning"
    """
    logger.info(f" Graph-enhanced search: {query}")
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    graph_retriever.search(
                        query=query, 
                        limit=limit, 
                        include_foundations=include_foundations,
                        filter_arxiv_ids=filter_arxiv_ids
                    )
                )
                result = future.result()
        else:
            result = loop.run_until_complete(
                graph_retriever.search(
                    query=query,
                    limit=limit,
                    include_foundations=include_foundations,
                    filter_arxiv_ids=filter_arxiv_ids
                )
            )
        
        papers = result.get('results', [])
        logger.info(f" Graph search found {len(papers)} papers")
        
        if filter_arxiv_ids:
            papers = [p for p in papers if p.get('arxiv_id') in filter_arxiv_ids]
            logger.info(f"Filtered to {len(papers)} focused papers: {filter_arxiv_ids}")
        
        sources = []
        for paper in papers:
            graph_meta = paper.get('graph_metadata', {})
            chunks = paper.get('chunks', [])
            
            citation_count = graph_meta.get('citation_count', 0)
            is_seminal = citation_count > 100
            is_foundational = graph_meta.get('is_foundational', False)
            cited_by_count = graph_meta.get('cited_by_results', 0)
            
            source = {
                "arxiv_id": paper.get('arxiv_id'),
                "title": paper.get('title'),
                "chunks_used": len(chunks),
                "citation_count": citation_count,
                "is_seminal": is_seminal,
                "is_foundational": is_foundational,
                "cited_by_results": cited_by_count,
                "chunk_details": [
                    {
                        "section": chunk.get('section_title', 'Content'),
                        "text_preview": chunk.get('chunk_text', '')[:200],
                        "score": chunk.get('score', 0.0)
                    }
                    for chunk in chunks[:3]
                ]
            }
            sources.append(source)
        
        logger.info(f"Built {len(sources)} sources with metadata")
        
        tool_result = {
            "tool_name": "search_papers_with_graph",
            "results": papers,
            "sources": sources,
            "graph_insights": result.get('graph_insights', {}),
        }

        _update_tool_cache(tool_result)

        return tool_result
    except Exception as e:
        logger.error(f"Graph search failed: {e}")
        logger.info("Falling back to regular search")
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        try:
            if loop is not None and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        graph_retriever.search(
                            query=query,
                            limit=limit,
                            include_foundations=False,
                            filter_arxiv_ids=filter_arxiv_ids,
                        ),
                    )
                    fallback_result = future.result()
            else:
                if loop is None:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                fallback_result = loop.run_until_complete(
                    graph_retriever.search(
                        query=query,
                        limit=limit,
                        include_foundations=False,
                        filter_arxiv_ids=filter_arxiv_ids,
                    )
                )

            return {
                "results": fallback_result.get("results", []),
                "sources": [],
                "fallback": True,
            }
        except Exception as e2:
            logger.error(f"Fallback graph search also failed: {e2}")
            return {
                "results": [],
                "sources": [],
                "fallback": True,
                "error": str(e2),
            }

@function_tool
def get_paper_details(arxiv_id: str) -> Dict[str, Any]:
    """
    Fetch detailed information about a specific paper by its arXiv ID.
    
    Use this tool when:
    - User asks about a specific paper by ID (e.g., "tell me about arXiv:2510.24450")
    - User says "this paper" or "the paper" when they have a paper focused
    - You need comprehensive details (abstract, authors, citations, content)
    
    Args:
        arxiv_id: The arXiv ID (e.g., "2510.24450v1" or "2510.24450")
    
    Returns:
        Dictionary with paper metadata, abstract, and sample content chunks
    """
    try:
        logger.info(f"Fetching detailed paper info for {arxiv_id}")
        
        clean_id = arxiv_id.replace("arXiv:", "").replace("arxiv:", "").strip()
        
        from src.database import get_sync_session
        from src.models.paper import Paper
        from src.services.knowledge_graph import Neo4jClient
        
        paper_metadata = None
        with get_sync_session() as db:
            paper_metadata = db.query(Paper).filter(Paper.arxiv_id == clean_id).first()
        
        if not paper_metadata:
            return {
                "error": f"Paper {clean_id} not found in database",
                "suggestion": "Try searching for it using search_papers_with_graph instead"
            }
        
        citation_count = 0
        is_seminal = False
        try:
            with Neo4jClient() as client:
                result = client.execute_query(
                    """
                    MATCH (p:Paper {arxiv_id: $arxiv_id})
                    OPTIONAL MATCH (cited:Paper)-[:CITES]->(p)
                    WITH p, count(DISTINCT cited) as citation_count
                    RETURN citation_count,
                           CASE WHEN citation_count > 100 THEN true ELSE false END as is_seminal
                    """,
                    {"arxiv_id": clean_id}
                )
                if result and len(result) > 0:
                    citation_count = result[0].get("citation_count", 0)
                    is_seminal = result[0].get("is_seminal", False)
        except Exception as e:
            logger.warning(f"Could not get citation data: {e}")
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    graph_retriever.vector_search(
                        clean_id,
                        limit=10,
                        exclude_sections=["References", "Bibliography"],
                    ),
                )
                chunks = future.result()
        else:
            if loop is None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            chunks = loop.run_until_complete(
                graph_retriever.vector_search(
                    clean_id,
                    limit=10,
                    exclude_sections=["References", "Bibliography"],
                )
            )
        
        result = {
            "arxiv_id": paper_metadata.arxiv_id,
            "title": paper_metadata.title,
            "abstract": paper_metadata.abstract,
            "authors": paper_metadata.authors if isinstance(paper_metadata.authors, list) else [],
            "published_date": paper_metadata.published_date.isoformat() if paper_metadata.published_date else "",
            "primary_category": paper_metadata.primary_category,
            "categories": paper_metadata.categories if isinstance(paper_metadata.categories, list) else [],
            "citation_count": citation_count,
            "is_seminal": is_seminal,
            "sample_content": [
                {
                    "section": chunk.get("section_title", "Content"),
                    "text": chunk.get("chunk_text", "")[:500]
                }
                for chunk in chunks[:3]
            ] if chunks else []
        }
        
        logger.info(f"Successfully fetched details for {clean_id}")

        sources: List[Dict[str, Any]] = [
            {
                "arxiv_id": result.get("arxiv_id"),
                "title": result.get("title"),
                "chunks_used": len(result.get("sample_content", [])),
                "citation_count": result.get("citation_count", 0),
                "is_seminal": result.get("is_seminal", False),
                "is_foundational": False,
                "cited_by_results": 0,
                "chunk_details": [
                    {
                        "section": c.get("section", "Content"),
                        "text_preview": c.get("text", "")[:200],
                        "score": 0.0,
                    }
                    for c in result.get("sample_content", [])[:3]
                ],
            }
        ]

        _update_tool_cache(
            {
                "tool_name": "get_paper_details",
                "results": [result],
                "sources": sources,
                "graph_insights": {},
            }
        )

        return result
        
    except Exception as e:
        logger.error(f"Failed to get paper details: {e}")
        return {
            "error": f"Failed to fetch paper: {str(e)}",
            "arxiv_id": arxiv_id
        }
