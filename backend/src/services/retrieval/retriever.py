from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.config import get_settings
from src.database import get_sync_session

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

settings = get_settings()

class Retriever:
    def __init__(self) -> None:

        self._db_session_ctx = get_sync_session

        self._qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        self._st_model = SentenceTransformer(settings.embedding_model_local)


    def vector_search(self, query: str, limit: int = 10, include_sections: Optional[List[str]] = None, exclude_sections: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Vector similarity search over chunk collection in Qdrant, returns chunk-level results."""
        from qdrant_client.http import models as qmodels
        print(f"Tool Called with Vector search: {query} | Limit: {limit} | Include Sections: {include_sections} | Exclude Sections: {exclude_sections}")
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

        q_vec = self._st_model.encode([query])[0].tolist()
        res = self._qdrant.search(
            collection_name=settings.qdrant_collection,
            query_vector=q_vec,
            limit=limit,
            with_vectors=False,
            with_payload=True,
            search_params=qmodels.SearchParams(
                hnsw_ef=None,
                exact=False,
            ),
            query_filter=filters,
        )
        results: List[Dict[str, Any]] = []
        for pt in res:
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
                    "source": "vector",
                }
            )
        return results

def get_retriever() -> Retriever:
    return Retriever()
