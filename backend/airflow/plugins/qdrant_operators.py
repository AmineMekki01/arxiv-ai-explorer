from __future__ import annotations

import os

from typing import Any, Dict, Optional

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels


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
        self.host = host or os.getenv("QDRANT_HOST", "qdrant")
        self.port = int(port or os.getenv("QDRANT_PORT", "6333"))
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
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION", "arxiv_chunks")
        self.vector_size = int(vector_size or os.getenv("EMBEDDING_DIM", "384"))
        self.distance = (distance or os.getenv("QDRANT_DISTANCE", "Cosine")).capitalize()
        self.payload_schema = payload_schema or {}
        self.hook_kwargs = hook_kwargs or {}

    def execute(self, context: Dict[str, Any]) -> str:
        hook = QdrantHook(**self.hook_kwargs)
        client = hook.get_client()

        if self.distance not in {"Cosine", "Euclid", "Dot"}:
            self.log.warning("Unknown distance '%s', defaulting to Cosine", self.distance)
            self.distance = "Cosine"
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
