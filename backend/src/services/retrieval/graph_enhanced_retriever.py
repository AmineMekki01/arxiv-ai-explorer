from __future__ import annotations

from typing import Any, Dict, List, Optional
from collections import defaultdict
from loguru import logger

from src.services.retrieval.retriever import Retriever
from src.services.knowledge_graph import Neo4jClient, GraphQueryService
from qdrant_client import QdrantClient
from src.config import get_settings

settings = get_settings()


class GraphEnhancedRetriever:
    """
    Enhanced retriever that combines vector search with graph intelligence.
    
    Flow:
    1. Retrieve chunks from Qdrant (hybrid search)
    2. Analyze papers using graph (citations, metadata)
    3. Re-rank chunks using graph features
    4. Add missing foundational papers
    5. Return smart-selected results
    """
    
    def __init__(self):
        self.retriever = Retriever()
        self.qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        include_foundations: bool = True,
        min_foundation_citations: int = 3,
        filter_arxiv_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform graph-enhanced search.
        
        Args:
            query: Search query
            limit: Number of final results
            include_foundations: Whether to add missing foundational papers
            min_foundation_citations: Minimum citations for foundation detection
            filter_arxiv_ids: Optional list of arXiv IDs to filter results (for focused mode)
            
        Returns:
            Dictionary with results and graph insights
        """
        if filter_arxiv_ids:
            logger.info(f"📌 Searching within focused papers: {filter_arxiv_ids}")
            chunks = self.retriever.vector_search(
                query, 
                limit=limit * 3,
                filter_arxiv_ids=filter_arxiv_ids
            )
        else:
            chunks = self.retriever.vector_search(query, limit=limit * 3)
        
        if not chunks:
            logger.info(f"No chunks found for query: {query}")
            return {
                "results": [],
                "graph_insights": {},
                "query": query
            }
        
        logger.info(f"Retrieved {len(chunks)} chunks from Qdrant for query: {query}")
        
        paper_ids = list(set([c["arxiv_id"] for c in chunks if c.get("arxiv_id")]))
        logger.info(f"Found {len(paper_ids)} unique papers in results")
        
        graph_insights = await self._analyze_with_graph(paper_ids)
        
        reranked_chunks = self._rerank_with_graph(chunks, graph_insights, query)
        
        foundation_chunks = []
        if include_foundations and graph_insights.get("missing_foundations"):
            foundation_chunks = await self._fetch_foundation_chunks(
                graph_insights["missing_foundations"],
                query
            )
            logger.info(f"Added {len(foundation_chunks)} foundation chunks")
        
        final_chunks = self._smart_select(
            foundation_chunks + reranked_chunks,
            limit=limit
        )
        
        results = self._group_chunks_by_paper(final_chunks, graph_insights)
        
        return {
            "results": results,
            "graph_insights": {
                "total_papers": len(paper_ids),
                "internal_citations": len(graph_insights.get("internal_citations", [])),
                "foundational_papers_added": len(foundation_chunks),
                "central_papers": self._identify_central_papers(
                    graph_insights.get("internal_citations", [])
                )
            },
            "query": query
        }
    
    async def _analyze_with_graph(self, paper_ids: List[str]) -> Dict[str, Any]:
        """Analyze papers using Neo4j graph."""
        if not paper_ids:
            return {}
        
        try:
            with Neo4jClient() as client:
                service = GraphQueryService(client)
                
                return {
                    "internal_citations": service.get_internal_citations(paper_ids),
                    "missing_foundations": service.find_missing_foundations(
                        paper_ids,
                        min_citations=3,
                        limit=2
                    ),
                    "papers_metadata": service.get_papers_metadata(paper_ids)
                }
        except Exception as e:
            logger.error(f"Graph analysis failed: {e}")
            return {}
    
    def _rerank_with_graph(
        self,
        chunks: List[Dict],
        graph_insights: Dict,
        query: str
    ) -> List[Dict]:
        """
        Re-rank chunks using graph features.
        
        Boosts:
        - Seminal papers (citation_count > 100)
        - Papers cited by other results (central)
        - Recent papers if query mentions "recent"
        """
        papers_metadata = graph_insights.get("papers_metadata", {})
        internal_citations = graph_insights.get("internal_citations", [])
        
        citation_counts = defaultdict(int)
        for edge in internal_citations:
            citation_counts[edge["target"]] += 1
        
        is_recent_query = any(word in query.lower() for word in ["recent", "latest", "new", "2024", "2023"])
        
        scored_chunks = []
        for chunk in chunks:
            arxiv_id = chunk.get("arxiv_id")
            if not arxiv_id:
                continue
            
            score = chunk.get("score", 0.5)
            metadata = papers_metadata.get(arxiv_id, {})
            
            if metadata.get("is_seminal"):
                score *= 1.3
                logger.debug(f"Seminal boost for {arxiv_id}: {score}")
            
            internal_cite_count = citation_counts.get(arxiv_id, 0)
            if internal_cite_count > 0:
                boost = 1 + (0.1 * internal_cite_count)
                score *= boost
                logger.debug(f"Centrality boost for {arxiv_id}: {boost}")
            
            if is_recent_query:
                published_date = chunk.get("published_date", "")
                if any(year in str(published_date) for year in ["2024", "2023"]):
                    score *= 1.2
                    logger.debug(f"Recency boost for {arxiv_id}")
            
            chunk["graph_metadata"] = {
                "citation_count": metadata.get("citation_count", 0),
                "is_seminal": metadata.get("is_seminal", False),
                "cited_by_results": internal_cite_count,
                "is_foundational": False
            }
            chunk["final_score"] = score
            
            scored_chunks.append(chunk)
        
        scored_chunks.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        logger.info(f"Re-ranked {len(scored_chunks)} chunks using graph features")
        
        return scored_chunks
    
    async def _fetch_foundation_chunks(
        self,
        foundations: List[Dict],
        original_query: str
    ) -> List[Dict]:
        """
        Fetch relevant chunks from foundational papers.
        
        Uses query-specific search within each foundation paper,
        not just "introduction" blindly.
        """
        from qdrant_client.http import models as qmodels
        from src.services.embeddings.multi_vector_embedder import MultiVectorEmbedder
        
        foundation_chunks = []
        embedder = MultiVectorEmbedder()
        
        for foundation in foundations:
            arxiv_id = foundation.get("arxiv_id")
            if not arxiv_id:
                continue
            
            try:
                query_embeddings = embedder.embed_query(original_query)
                dense_vector = query_embeddings["dense"].tolist()
                sparse_vector = query_embeddings["sparse"].as_object()
                
                paper_filter = qmodels.Filter(
                    must=[qmodels.FieldCondition(
                        key="arxiv_id",
                        match=qmodels.MatchValue(value=arxiv_id)
                    )]
                )
                
                prefetch_dense = qmodels.Prefetch(
                    query=dense_vector,
                    using="all-MiniLM-L6-v2",
                    limit=2,
                )
                
                prefetch_sparse = qmodels.Prefetch(
                    query=qmodels.SparseVector(
                        indices=sparse_vector["indices"],
                        values=sparse_vector["values"]
                    ),
                    using="bm25",
                    limit=2,
                )
                
                res = self.qdrant.query_points(
                    collection_name=settings.qdrant_collection,
                    prefetch=[prefetch_dense, prefetch_sparse],
                    query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
                    limit=1,
                    with_payload=True,
                    query_filter=paper_filter,
                )
                
                points = res.points if hasattr(res, 'points') else res
                if points:
                    chunk = points[0]
                    pay = chunk.payload or {}
                    foundation_chunk = {
                        "type": "chunk",
                        "arxiv_id": pay.get("arxiv_id"),
                        "title": pay.get("title"),
                        "section_title": pay.get("section_title"),
                        "section_type": pay.get("section_type"),
                        "chunk_index": pay.get("chunk_index"),
                        "chunk_text": pay.get("chunk_text"),
                        "primary_category": pay.get("primary_category"),
                        "categories": pay.get("categories", []),
                        "published_date": pay.get("published_date"),
                        "score": float(chunk.score) if chunk.score is not None else 0.0,
                        "source": "foundation",
                        "graph_metadata": {
                            "citation_count": foundation.get("total_citations", 0),
                            "is_seminal": True,
                            "cited_by_results": foundation.get("cited_by_results", 0),
                            "is_foundational": True
                        },
                        "final_score": 1.5
                    }
                    foundation_chunks.append(foundation_chunk)
                    logger.info(f"Fetched foundation chunk from {arxiv_id}")
            
            except Exception as e:
                logger.error(f"Failed to fetch foundation chunk for {arxiv_id}: {e}")
                continue
        
        return foundation_chunks
    
    def _smart_select(self, chunks: List[Dict], limit: int) -> List[Dict]:
        """
        Smart selection ensuring diversity across papers.
        
        Strategy:
        - Always include top chunk
        - Include foundational papers
        - Ensure diverse paper coverage
        - Then fill with high-score chunks
        """
        if not chunks:
            return []
        
        selected = []
        papers_included = set()
        
        if chunks:
            selected.append(chunks[0])
            papers_included.add(chunks[0]["arxiv_id"])
        
        for chunk in chunks:
            if chunk.get("graph_metadata", {}).get("is_foundational"):
                if chunk not in selected:
                    selected.append(chunk)
                    papers_included.add(chunk["arxiv_id"])
        
        for chunk in chunks:
            if len(selected) >= limit:
                break
            if chunk["arxiv_id"] not in papers_included:
                selected.append(chunk)
                papers_included.add(chunk["arxiv_id"])
        
        for chunk in chunks:
            if len(selected) >= limit:
                break
            if chunk not in selected:
                selected.append(chunk)
        
        logger.info(f"Smart-selected {len(selected)} chunks from {len(papers_included)} papers")
        return selected[:limit]
    
    def _group_chunks_by_paper(
        self,
        chunks: List[Dict],
        graph_insights: Dict
    ) -> List[Dict]:
        """Group chunks by paper and add paper-level metadata."""
        papers = {}
        
        for chunk in chunks:
            arxiv_id = chunk["arxiv_id"]
            if arxiv_id not in papers:
                papers[arxiv_id] = {
                    "arxiv_id": arxiv_id,
                    "title": chunk["title"],
                    "published_date": chunk.get("published_date"),
                    "primary_category": chunk.get("primary_category"),
                    "categories": chunk.get("categories", []),
                    "chunks": [],
                    "graph_metadata": chunk.get("graph_metadata", {}),
                    "max_score": chunk.get("final_score", 0)
                }
            
            papers[arxiv_id]["chunks"].append({
                "chunk_text": chunk["chunk_text"],
                "section_title": chunk.get("section_title"),
                "section_type": chunk.get("section_type"),
                "chunk_index": chunk.get("chunk_index"),
                "score": chunk.get("score")
            })
            
            current_score = chunk.get("final_score", 0)
            if current_score > papers[arxiv_id]["max_score"]:
                papers[arxiv_id]["max_score"] = current_score
        
        results = sorted(papers.values(), key=lambda x: x["max_score"], reverse=True)
        logger.info(f"Grouped into {len(results)} papers")
        
        return results
    
    def _identify_central_papers(self, internal_citations: List[Dict]) -> List[str]:
        """Identify papers that are cited by many others in the result set."""
        citation_counts = defaultdict(int)
        for edge in internal_citations:
            citation_counts[edge["target"]] += 1
        
        central = [
            arxiv_id for arxiv_id, count in citation_counts.items()
            if count >= 2
        ]
        return central


def get_graph_enhanced_retriever() -> GraphEnhancedRetriever:
    """Factory function for graph-enhanced retriever."""
    return GraphEnhancedRetriever()
