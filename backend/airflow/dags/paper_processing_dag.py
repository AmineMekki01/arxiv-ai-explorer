from __future__ import annotations

import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

sys.path.insert(0, "/opt/airflow")

from plugins.arxiv_operators import (
    LoadPapersForEmbeddingOperator,
    ChunkDocumentsOperator,
    GenerateEmbeddingsOperator,
    MarkPapersEmbeddedOperator,
)
from plugins.qdrant_operators import (
    EnsureCollectionOperator,
    UpsertPointsOperator,
)

DAG_ID = "paper_processing_pipeline"

default_args = {
    "owner": "researchmind",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id=DAG_ID,
    description="Chunk, embed, and index papers into Qdrant",
    default_args=default_args,
    schedule_interval="0 2 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["papers", "processing", "embeddings", "qdrant"],
) as dag:

    start = EmptyOperator(
        task_id="start",
        doc_md="Start of the paper processing pipeline",
    )

    load_papers = LoadPapersForEmbeddingOperator(
        task_id="load_papers_for_embedding",
        max_papers=100,
        doc_md="Load papers from PostgreSQL that need embeddings",
    )

    ensure_qdrant = EnsureCollectionOperator(
        task_id="ensure_qdrant_collection",
        doc_md="Ensure Qdrant collection exists",
    )

    chunk_docs = ChunkDocumentsOperator(
        task_id="chunk_documents",
        input_task_id="load_papers_for_embedding",
        doc_md="Create section-aware overlapping chunks from paper content",
    )

    embed_chunks = GenerateEmbeddingsOperator(
        task_id="generate_embeddings",
        input_task_id="chunk_documents",
        doc_md="Generate embeddings for chunks using SentenceTransformers",
    )

    upsert_qdrant = UpsertPointsOperator(
        task_id="upsert_qdrant",
        input_task_id="generate_embeddings",
        doc_md="Upsert chunk vectors into Qdrant",
    )

    mark_embedded = MarkPapersEmbeddedOperator(
        task_id="mark_papers_embedded",
        input_task_id="generate_embeddings",
        doc_md="Mark processed papers as embedded in PostgreSQL",
    )

    end = EmptyOperator(
        task_id="end",
        trigger_rule=TriggerRule.ALL_DONE,
        doc_md="End of the paper processing pipeline",
    )

    start >> load_papers >> ensure_qdrant >> chunk_docs >> embed_chunks >> upsert_qdrant >> mark_embedded >> end
