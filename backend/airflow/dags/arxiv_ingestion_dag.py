from __future__ import annotations
import sys

from datetime import datetime, timedelta
from airflow import DAG
from airflow.utils.trigger_rule import TriggerRule
from airflow.operators.empty import EmptyOperator
sys.path.insert(0, "/opt/airflow")


from plugins.arxiv_operators import (
    FetchArxivOperator,
    ParsePDFOperator,
    ExtractMetadataOperator,
    PersistDBOperator,
)

DAG_ID = "arxiv_daily_ingestion"

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
    description="Daily arXiv paper ingestion pipeline",
    default_args=default_args,
    schedule_interval="0 6 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["arxiv", "ingestion", "daily"],
) as dag:
    
    start = EmptyOperator(
        task_id="start",
        doc_md="Start of the arXiv ingestion pipeline"
    )

    fetch_papers = FetchArxivOperator(
        task_id="fetch_papers",
        since_days=1,
        doc_md="Fetch recent papers from arXiv API for configured categories"
    )

    parse_pdfs = ParsePDFOperator(
        task_id="parse_pdfs",
        input_task_id="fetch_papers",
        doc_md="Parse PDF content using existing PDFParser service"
    )

    extract_metadata = ExtractMetadataOperator(
        task_id="extract_metadata",
        input_task_id="parse_pdfs",
        doc_md="Extract enhanced metadata using MetadataExtractor service"
    )

    persist_db = PersistDBOperator(
        task_id="persist_db",
        input_task_id="extract_metadata",
        doc_md="Persist papers to PostgreSQL database using existing models"
    )

    end = EmptyOperator(
        task_id="end",
        trigger_rule=TriggerRule.ALL_DONE,
        doc_md="End of the ingestion pipeline"
    )

    start >> fetch_papers >> parse_pdfs >> extract_metadata >> persist_db >> end