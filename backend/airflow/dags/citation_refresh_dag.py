"""
Citation Refresh DAG - Periodic updates of citation data.

This DAG runs weekly to refresh citation counts for papers, as citations
grow over time. It prioritizes highly-cited papers and those that haven't
been updated recently.
"""
from __future__ import annotations
import sys

from datetime import datetime, timedelta
from airflow import DAG
from airflow.utils.trigger_rule import TriggerRule
from airflow.operators.empty import EmptyOperator

sys.path.insert(0, "/opt/airflow")

from plugins.citation_operators import (
    FindStaleCitationsOperator,
    ExtractCitationsOperator,
)
from plugins.kg_operators import UpdateCitationNetworkOperator

DAG_ID = "citation_refresh_pipeline"

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
    description="Weekly refresh of citation data for existing papers",
    default_args=default_args,
    schedule_interval="0 4 * * 0",
    catchup=False,
    max_active_runs=1,
    tags=["citations", "refresh", "weekly"],
) as dag:
    
    start = EmptyOperator(
        task_id="start",
        doc_md="Start of the citation refresh pipeline"
    )

    find_stale = FindStaleCitationsOperator(
        task_id="find_stale_papers",
        min_age_days=7,
        max_papers=500,
        doc_md="Find papers with stale citation data that need refreshing"
    )

    refresh_citations = ExtractCitationsOperator(
        task_id="refresh_citations",
        input_task_id="find_stale_papers",
        batch_size=5,
        max_papers=500,
        only_missing=False,
        doc_md="Re-extract citations from Semantic Scholar to get updated counts"
    )

    update_citation_network = UpdateCitationNetworkOperator(
        task_id="update_citation_network",
        input_task_id="find_stale_papers",
        doc_md="Update citation relationships in knowledge graph with refreshed data"
    )

    end = EmptyOperator(
        task_id="end",
        trigger_rule=TriggerRule.ALL_DONE,
        doc_md="End of the citation refresh pipeline"
    )

    start >> find_stale >> refresh_citations >> update_citation_network >> end
