from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.config import get_settings
from src.database import get_sync_session

from qdrant_client import QdrantClient
from src.services.embeddings.multi_vector_embedder import MultiVectorEmbedder

settings = get_settings()

class Retriever:
    def __init__(self) -> None:

        self._db_session_ctx = get_sync_session

        self._qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        self._embedder = MultiVectorEmbedder()


    def vector_search(self, query: str, limit: int = 10, include_sections: Optional[List[str]] = None, exclude_sections: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Hybrid search using both dense and sparse embeddings with rank fusion."""
        from qdrant_client.http import models as qmodels
        print(f"Tool Called with Hybrid search: {query} | Limit: {limit} | Include Sections: {include_sections} | Exclude Sections: {exclude_sections}")
        
        filters = None
        if include_sections:
            filters = qmodels.Filter(
                must=[qmodels.FieldCondition(
                    key="section_title",
                    match=qmodels.MatchAny(any=include_sections)
                )]
            )
        elif exclude_sections:
            filters = qmodels.Filter(
                must_not=[qmodels.FieldCondition(
                    key="section_title",
                    match=qmodels.MatchAny(any=exclude_sections)
                )]
            )

        query_embeddings = self._embedder.embed_query(query)
        dense_vector = query_embeddings["dense"].tolist()
        sparse_vector = query_embeddings["sparse"].as_object()
        
        prefetch_dense = qmodels.Prefetch(
            query=dense_vector,
            using="all-MiniLM-L6-v2",
            limit=limit * 2,
        )
        
        prefetch_sparse = qmodels.Prefetch(
            query=qmodels.SparseVector(
                indices=sparse_vector["indices"],
                values=sparse_vector["values"]
            ),
            using="bm25",
            limit=limit * 2,
        )
        
        res = self._qdrant.query_points(
            collection_name=settings.qdrant_collection,
            prefetch=[prefetch_dense, prefetch_sparse],
            query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
            limit=limit,
            with_payload=True,
            query_filter=filters,
        )
        
        results: List[Dict[str, Any]] = []
        points = res.points if hasattr(res, 'points') else res
        for pt in points:
            pay = pt.payload or {}
            results.append(
                {
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
                    "score": float(pt.score) if pt.score is not None else None,
                    "source": "hybrid",
                }
            )
        return results

def get_retriever() -> Retriever:
    return Retriever()
