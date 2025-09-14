from __future__ import annotations

import os
import sys

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

import sys
sys.path.insert(0, "/opt/airflow")

from src.services.arxiv.client import ArxivClient
from src.services.arxiv.parser import PDFParser
from src.services.arxiv.metadata_extractor import MetadataExtractor
from src.database import get_sync_session
from src.models.paper import Paper

class FetchArxivOperator(BaseOperator):
    """
    Fetch recent arXiv papers for configured categories using existing ArxivClient.
    Returns XCom: list[dict] with paper metadata.
    """
    @apply_defaults
    def __init__(
        self,
        categories: Optional[List[str]] = None,
        max_results: Optional[int] = None,
        since_days: int = 1,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        cats_env = os.getenv("ARXIV_CATEGORIES", "cs.AI,cs.CL,cs.LG")
        self.categories = categories or [c.strip() for c in cats_env.split(",") if c.strip()]
        self.max_results = int(max_results or os.getenv("ARXIV_MAX_RESULTS", "50"))
        self.since_days = since_days

    def execute(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        client = ArxivClient()        
        papers = []
        for category in self.categories:
            try:
                category_papers = asyncio.run(
                    client.search_papers(
                        query=f"cat:{category}",
                        max_results=self.max_results // len(self.categories),
                        sort_by="submittedDate",
                        sort_order="descending"
                    )
                )
                papers.extend(category_papers)
            except Exception as e:
                self.log.warning(f"Failed to fetch papers for category {category}: {e}")

        return papers

class ParsePDFOperator(BaseOperator):
    """
    Parse PDF content using existing PDFParser service.
    """
    @apply_defaults
    def __init__(self, input_task_id: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.input_task_id = input_task_id

    def execute(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        ti = context["ti"]
        papers: List[Dict[str, Any]] = ti.xcom_pull(task_ids=self.input_task_id) or []
        
        parser = PDFParser()
        for paper in papers:
            try:
                if paper.get("pdf_url"):
                    content = asyncio.run(parser.parse_pdf(paper["pdf_url"]))
                    paper["content"] = content.get("text", "")
                    paper["sections"] = content.get("sections", [])
                    paper["figures"] = content.get("figures", [])
                    paper["tables"] = content.get("tables", [])
            except Exception as e:
                self.log.warning(f"Failed to parse PDF for {paper.get('arxiv_id')}: {e}")
                paper["content"] = ""
                paper["sections"] = []
        
        return papers


class ExtractMetadataOperator(BaseOperator):
    """
    Extract enhanced metadata using existing MetadataExtractor service.
    """
    @apply_defaults
    def __init__(self, input_task_id: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.input_task_id = input_task_id

    def execute(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        ti = context["ti"]
        papers: List[Dict[str, Any]] = ti.xcom_pull(task_ids=self.input_task_id) or []
        
        extractor = MetadataExtractor()
        for paper in papers:
            try:
                metadata = asyncio.run(extractor.extract_metadata(paper))
                paper.update(metadata)
            except Exception as e:
                self.log.warning(f"Failed to extract metadata for {paper.get('arxiv_id')}: {e}")
    
        return papers


class PersistDBOperator(BaseOperator):
    """
    Persist papers to PostgreSQL using existing database models.
    """
    @apply_defaults
    def __init__(self, input_task_id: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.input_task_id = input_task_id
    
    def _normalize_paper(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize paper data to match SQLAlchemy model fields."""
        def to_dt(s: Optional[str]) -> Optional[datetime]:
            if not s:
                return None
            try:
                if isinstance(s, str) and s.endswith("Z"):
                    s = s.replace("Z", "+00:00")
                return datetime.fromisoformat(s) if isinstance(s, str) else s
            except Exception:
                return None
        
        def sanitize_text(text: Optional[str]) -> Optional[str]:
            """Remove NUL characters and other problematic characters from text."""
            if not text or not isinstance(text, str):
                return text
            sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t\r')
            return sanitized.strip() if sanitized else None

        normalized: Dict[str, Any] = {}
        
        normalized["arxiv_id"] = data.get("arxiv_id")
        normalized["arxiv_url"] = sanitize_text(data.get("abs_url") or data.get("arxiv_url")) or ""
        normalized["pdf_url"] = sanitize_text(data.get("pdf_url")) or ""
        normalized["title"] = sanitize_text(data.get("title")) or "Untitled"
        normalized["abstract"] = sanitize_text(data.get("abstract") or data.get("summary")) or ""
        normalized["authors"] = data.get("authors") or []
        normalized["published_date"] = to_dt(data.get("published")) or data.get("published_date") or datetime.now()
        normalized["updated_date"] = to_dt(data.get("updated")) or data.get("updated_date")
        
        normalized["version"] = 1
        try:
            vid = data.get("arxiv_id", "")
            if isinstance(vid, str) and "v" in vid and vid.split("v")[-1].isdigit():
                normalized["version"] = int(vid.split("v")[-1])
        except Exception:
            pass
        
        normalized["primary_category"] = sanitize_text(data.get("primary_category")) or "unknown"
        normalized["categories"] = data.get("categories") or []
        
        normalized["is_processed"] = data.get("is_processed", False)
        normalized["is_embedded"] = data.get("is_embedded", False)
        normalized["citation_count"] = data.get("citation_count", 0)
        normalized["download_count"] = data.get("download_count", 0)
        
        normalized["full_text"] = sanitize_text(data.get("content") or data.get("full_text"))
        normalized["embedding_model"] = sanitize_text(data.get("embedding_model"))
        normalized["embedding_vector"] = sanitize_text(data.get("embedding_vector"))
        normalized["local_pdf_path"] = sanitize_text(data.get("local_pdf_path"))
        normalized["local_text_path"] = sanitize_text(data.get("local_text_path"))
        
        return {k: v for k, v in normalized.items() if v is not None}

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ti = context["ti"]
        papers: List[Dict[str, Any]] = ti.xcom_pull(task_ids=self.input_task_id) or []
        
        self.log.info(f"Processing {len(papers)} papers for persistence")
        if not papers:
            return {"persisted": 0, "skipped": 0}
        
        if not get_sync_session or not Paper:
            self.log.error("Database session or Paper model not available")
            return {"persisted": 0, "skipped": 0, "error": "Database not configured"}
            
        persisted = 0
        skipped = 0
        
        try:
            with get_sync_session() as session:
                self.log.info("Database session created successfully")
            
                for i, raw in enumerate(papers):
                    try:
                        data = self._normalize_paper(raw)
                        
                        if not data.get("arxiv_id"):
                            self.log.warning("Skipping paper with no arxiv_id")
                            skipped += 1
                            continue
                        
                        existing = session.query(Paper).filter_by(arxiv_id=data.get("arxiv_id")).first()
                        
                        if existing:
                            self.log.info(f"Paper {data.get('arxiv_id')} exists, updating...")
                            for key, value in data.items():
                                if hasattr(existing, key) and key != 'id':
                                    try:
                                        setattr(existing, key, value)
                                    except Exception as e:
                                        self.log.error(f"Error updating field {key}: {e}")
                            skipped += 1
                            self.log.info(f"Updated existing paper {data.get('arxiv_id')}")
                        else:
                            self.log.info(f"Creating new paper {data.get('arxiv_id')}...")
                            filtered_data = {k: v for k, v in data.items() if hasattr(Paper, k) and v is not None}
                            try:
                                paper = Paper(**filtered_data)
                                session.add(paper)
                                self.log.info(f"Successfully created paper object for {data.get('arxiv_id')}")
                                persisted += 1
                            except Exception as e:
                                self.log.error(f"Error creating paper {data.get('arxiv_id')}: {e}")
                                raise
                            self.log.info(f"Added new paper {data.get('arxiv_id')} to session")
                    except Exception as e:
                        self.log.error(f"Failed to persist paper {raw.get('arxiv_id')}: {e}", exc_info=True)
                        try:
                            session.rollback()
                            self.log.info("Session rolled back after error")
                        except Exception as rollback_error:
                            self.log.error(f"Failed to rollback session: {rollback_error}")
                        skipped += 1
                        continue
                
                if persisted > 0:
                    self.log.info(f"Committing session with {persisted} new papers and {skipped} skipped...")
                    try:
                        session.commit()
                        self.log.info("Session committed successfully")
                    except Exception as commit_error:
                        self.log.error(f"Failed to commit session: {commit_error}", exc_info=True)
                        session.rollback()
                        return {"persisted": 0, "skipped": 0, "error": str(commit_error)}
                
                return {"persisted": persisted, "skipped": skipped}
                
        except Exception as e:
            self.log.error(f"Unexpected error in PersistDBOperator: {e}", exc_info=True)
            return {"persisted": 0, "skipped": 0, "error": str(e)}
