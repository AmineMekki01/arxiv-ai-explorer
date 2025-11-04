from __future__ import annotations
import sys

from datetime import datetime, timedelta
from airflow import DAG
from airflow.utils.trigger_rule import TriggerRule
from airflow.operators.empty import EmptyOperator

sys.path.insert(0, "/opt/airflow")

from plugins.kg_operators import (
    InitializeKGSchemaOperator,
    BuildKnowledgeGraphOperator,
    GetGraphStatsOperator,
)

DAG_ID = "kg_initialization"

default_args = {
    "owner": "researchmind",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id=DAG_ID,
    description="Initialize Knowledge Graph schema and optionally backfill existing papers",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    tags=["knowledge-graph", "initialization", "one-time"],
) as dag:
    
    start = EmptyOperator(
        task_id="start",
        doc_md="Start of KG initialization"
    )

    init_schema = InitializeKGSchemaOperator(
        task_id="initialize_schema",
        doc_md="""
        Create Neo4j constraints and indexes:
        - Unique constraints on arxiv_id, author_id, concept names
        - Indexes for efficient queries on titles, dates, categories
        """
    )

    backfill_papers = BuildKnowledgeGraphOperator(
        task_id="backfill_papers",
        max_papers=None,
        doc_md="""
        Build knowledge graph for existing papers in database.
        
        This will:
        1. Load papers from PostgreSQL
        2. Create paper, author, concept, institution nodes
        3. Create citation relationships from S2 data
        
        Can be configured with max_papers to process in batches.
        Run multiple times if needed for large databases.
        """
    )

    get_stats = GetGraphStatsOperator(
        task_id="get_final_stats",
        trigger_rule=TriggerRule.ALL_DONE,
        doc_md="Get final graph statistics to verify successful initialization"
    )

    end = EmptyOperator(
        task_id="end",
        trigger_rule=TriggerRule.ALL_DONE,
        doc_md="End of KG initialization"
    )

    start >> init_schema >> backfill_papers >> get_stats >> end
