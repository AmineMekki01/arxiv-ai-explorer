from __future__ import annotations

import os

from typing import Any, Dict, Optional

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from src.config import get_settings

settings = get_settings()

class QdrantHook:
    """Simple hook to manage a Qdrant client based on environment variables."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: int = 30,
        https: bool = False,
    ) -> None:
        if QdrantClient is None:
            raise ImportError(
                "qdrant-client is required. Please add it to your environment (pip install qdrant-client)."
            )
        self.host = host or settings.qdrant_host
        self.port = int(port or settings.qdrant_port)
        self.timeout = timeout
        self.https = https

    def get_client(self) -> Any:
        return QdrantClient(
            host=self.host,
            port=self.port,
            prefer_grpc=False,
            https=self.https,
            timeout=self.timeout,
        )


class EnsureCollectionOperator(BaseOperator):
    """Ensure a Qdrant collection exists with the specified parameters."""

    @apply_defaults
    def __init__(
        self,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None,
        distance: Optional[str] = None,
        payload_schema: Optional[Dict[str, Any]] = None,
        hook_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.collection_name = collection_name or settings.qdrant_collection
        self.vector_size = int(vector_size or settings.embedding_dim)
        self.distance = (distance or settings.qdrant_distance).upper()
        self.payload_schema = payload_schema or {}
        self.hook_kwargs = hook_kwargs or {}

    def execute(self, context: Dict[str, Any]) -> str:
        hook = QdrantHook(**self.hook_kwargs)
        client = hook.get_client()

        if self.distance not in {"COSINE", "EUCLID", "DOT"}:
            self.log.warning("Unknown distance '%s', defaulting to COSINE", self.distance)
            self.distance = "COSINE"
        distance_enum = getattr(qmodels, "Distance")[self.distance]

        collections = client.get_collections().collections
        existing = any(c.name == self.collection_name for c in collections)
        if not existing:
            self.log.info(
                "Creating Qdrant collection '%s' (size=%s, distance=%s)",
                self.collection_name,
                self.vector_size,
                self.distance,
            )
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self.vector_size,
                    distance=distance_enum,
                ),
            )
        else:
            self.log.info("Qdrant collection '%s' already exists", self.collection_name)

        return self.collection_name


class UpsertPointsOperator(BaseOperator):
    """
    Upsert vector points (chunks) into a Qdrant collection.
    Expects input XCom payload: { 'papers': List[Dict], 'chunks': List[Dict] }
    Each chunk must have 'vector' (list[float]) and will be written with payload metadata.
    """

    @apply_defaults
    def __init__(
        self,
        input_task_id: str,
        collection_name: Optional[str] = None,
        batch_size: int = 256,
        hook_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.input_task_id = input_task_id
        self.collection_name = collection_name or settings.qdrant_collection
        self.batch_size = batch_size
        self.hook_kwargs = hook_kwargs or {}

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ti = context["ti"]
        payload: Dict[str, Any] = ti.xcom_pull(task_ids=self.input_task_id) or {}
        chunks = payload.get("chunks") or []

        if not chunks:
            self.log.warning("No chunks to upsert to Qdrant")
            return {"upserted": 0}

        hook = QdrantHook(**self.hook_kwargs)
        client = hook.get_client()

        upserted = 0
        batch_vectors: list[list[float]] = []
        batch_payloads: list[Dict[str, Any]] = []
        batch_ids: list[str] = []

        def flush_batch():
            nonlocal upserted, batch_vectors, batch_payloads, batch_ids
            if not batch_vectors:
                return
            points = [
                qmodels.PointStruct(id=pid, vector=vec, payload=pay)
                for pid, vec, pay in zip(batch_ids, batch_vectors, batch_payloads)
            ]
            client.upsert(collection_name=self.collection_name, points=points)
            upserted += len(points)
            batch_vectors = []
            batch_payloads = []
            batch_ids = []

        for idx, ch in enumerate(chunks):
            vec = ch.get("vector")
            if not vec:
                continue
            import hashlib
            content_id = f"{ch.get('arxiv_id','unknown')}_{ch.get('section_type','content')}_{ch.get('chunk_index',idx)}"
            pid = int(hashlib.sha256(content_id.encode('utf-8')).hexdigest(), 16) % (2**63 - 1)
            payload = {k: v for k, v in ch.items() if k not in {"vector"}}

            batch_ids.append(pid)
            batch_vectors.append(vec)
            batch_payloads.append(payload)

            if len(batch_vectors) >= self.batch_size:
                flush_batch()

        flush_batch()

        self.log.info(f"Upserted {upserted} chunk vectors into Qdrant collection '{self.collection_name}'")
        return {"upserted": upserted}
