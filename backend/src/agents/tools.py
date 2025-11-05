from typing import Any, Dict, List, Optional
import asyncio
from loguru import logger
from datetime import datetime

from src.services.retrieval.retriever import Retriever
from src.services.retrieval.graph_enhanced_retriever import GraphEnhancedRetriever
from agents import function_tool

retriever = Retriever()
graph_retriever = GraphEnhancedRetriever()

_last_tool_result = None
_last_tool_timestamp = None

def get_last_tool_result() -> Optional[Dict[str, Any]]:
    """Get the last tool result from cache."""
    return _last_tool_result

@function_tool
def search_papers(
    query: str,
    limit: int = 10,
    exclude_sections: Optional[List[str]] = None,
    include_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Basic vector similarity search (use search_papers_with_graph instead for better results).
    
    This is a simple, fast search tool for specific paper lookups.
    ⚠️ For research questions, use search_papers_with_graph instead - it provides:
    - Citation network analysis
    - Foundational paper discovery
    - Better ranking using graph intelligence
    
    Use this tool ONLY for:
    - Looking up a specific arXiv ID (e.g., "arXiv:1706.03762")
    - Finding a paper by exact author name
    - Quick fact-checking when you know the paper title
    - Simple queries where graph analysis isn't needed
    
    For most research queries, prefer search_papers_with_graph.
    
    Args:
        query: The search query (arXiv ID, paper title, or author name).
        limit: The number of results to return.
        exclude_sections: List of section titles to ignore.
        include_sections: List of section titles to only consider.
    Returns:
        A dictionary containing basic search results (no graph metadata).
    """
    print(f"Tool Called with Search papers: {query}")
    results = retriever.vector_search(query, limit=limit, exclude_sections=exclude_sections, include_sections=include_sections)

    return results

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
    logger.info(f"🔍 Graph-enhanced search: {query}")
    
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
            logger.info(f"📌 Filtered to {len(papers)} focused papers: {filter_arxiv_ids}")
        
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
        
        logger.info(f" Built {len(sources)} sources with metadata")
        
        tool_result = {
            "results": papers,
            "sources": sources,
            "graph_insights": result.get('graph_insights', {})
        }
        
        global _last_tool_result, _last_tool_timestamp
        _last_tool_result = tool_result
        _last_tool_timestamp = datetime.now()
        logger.info(f" Cached tool result with {len(sources)} sources")
        
        return tool_result
    except Exception as e:
        logger.error(f" Graph search failed: {e}")
        logger.info(" Falling back to regular search")
        
        results = retriever.vector_search(query, limit=limit)
        return {
            "results": results,
            "sources": [],
            "fallback": True
        }
