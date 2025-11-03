"""
Airflow operators for citation extraction from Semantic Scholar.
"""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from airflow.models import BaseOperator
from airflow.utils.context import Context
from sqlalchemy import select

from src.database import get_sync_session
from src.models.paper import Paper
from src.services.arxiv.citation_extractor import CitationExtractor
from src.core import logger


class ExtractCitationsOperator(BaseOperator):
    """
    Extract citations and references from Semantic Scholar for papers.
    
    Args:
        input_task_id: Task ID that provides paper data (optional)
        batch_size: Number of papers to process concurrently
        max_papers: Maximum papers to process in one run
        only_missing: If True, only process papers without citation data
        min_age_days: Only update papers older than this many days
    """
    
    template_fields = ["input_task_id"]
    
    def __init__(
        self,
        input_task_id: str = None,
        batch_size: int = 5,
        max_papers: int = 500,
        only_missing: bool = True,
        min_age_days: int = 0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.input_task_id = input_task_id
        self.batch_size = batch_size
        self.max_papers = max_papers
        self.only_missing = only_missing
        self.min_age_days = min_age_days
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Extract citations for papers."""
        
        papers = self._load_papers(context)
        
        if not papers:
            self.log.info("📭 No papers found for citation extraction")
            return {"processed": 0, "success": 0, "failed": 0}
        
        self.log.info(f"📊 Found {len(papers)} papers for citation extraction")
        
        return asyncio.run(self._run_extraction(papers))
    
    async def _run_extraction(self, papers: List[Paper]) -> Dict[str, Any]:
        """Run extraction in a single async context to avoid event loop issues."""
        extractor = CitationExtractor()
        results = []
        success_count = 0
        failed_count = 0
        
        try:
            for i in range(0, len(papers), self.batch_size):
                batch = papers[i:i + self.batch_size]
                self.log.info(f"🔄 Processing batch {i // self.batch_size + 1}/{(len(papers) - 1) // self.batch_size + 1}")
                
                batch_results = await self._process_batch(batch, extractor)
                results.extend(batch_results)
                
                for result in batch_results:
                    if result.get("source") != "none":
                        success_count += 1
                    else:
                        failed_count += 1
                
                self._save_to_db(batch_results)
                
                if i + self.batch_size < len(papers):
                    sleep_time = 2
                    self.log.info(f"⏳ Rate limiting: sleeping {sleep_time}s")
                    await asyncio.sleep(sleep_time)
        finally:
            await extractor.close()
        
        summary = {
            "processed": len(papers),
            "success": success_count,
            "failed": failed_count,
            "success_rate": f"{success_count / len(papers) * 100:.1f}%" if papers else "0%"
        }
        
        self.log.info(f"✅ Citation extraction complete: {summary}")
        return summary
    
    def _load_papers(self, context: Context) -> List[Paper]:
        """Load papers that need citation extraction.

        Robustly handles XCom payloads that may be:
        - a JSON string
        - a plain string arxiv_id
        - a list of strings
        - a list of dicts with key 'arxiv_id' (or 'arxivId')
        - a dict containing a list under common keys
        """
        
        def extract_arxiv_ids(payload) -> List[str]:
            ids: List[str] = []
            if payload is None:
                return ids
            if isinstance(payload, str):
                print("instance of string")
                try:
                    parsed = json.loads(payload)
                    return extract_arxiv_ids(parsed)
                except Exception:
                    return [payload]
            if isinstance(payload, list):
                print("instance of list")
                for item in payload:
                    if isinstance(item, str):
                        ids.append(item)
                    elif isinstance(item, dict):
                        aid = item.get("arxiv_id") or item.get("arxivId")
                        if aid:
                            ids.append(aid)
                return ids
            if isinstance(payload, dict):
                print("instance of dict")
                for key in ("papers", "items", "results", "data"):
                    if key in payload:
                        ids.extend(extract_arxiv_ids(payload[key]))
                single = payload.get("arxiv_id") or payload.get("arxivId")
                if single:
                    ids.append(single)
                return ids
            return ids
        
        if self.input_task_id:
            paper_data = context["ti"].xcom_pull(task_ids=self.input_task_id)
            arxiv_ids = extract_arxiv_ids(paper_data)
            if arxiv_ids:
                with get_sync_session() as session:
                    papers = session.execute(
                        select(Paper).where(Paper.arxiv_id.in_(arxiv_ids))
                    ).scalars().all()
                    return list(papers)
        
        with get_sync_session() as session:
            query = select(Paper).where(Paper.is_processed == True)
            
            if self.only_missing:
                query = query.where(Paper.s2_paper_id == None)
            
            if self.min_age_days > 0:
                cutoff = datetime.now(timezone.utc) - timedelta(days=self.min_age_days)
                query = query.where(
                    (Paper.last_citation_update < cutoff) | (Paper.last_citation_update == None)
                )
            
            query = query.limit(self.max_papers)
            
            papers = session.execute(query).scalars().all()
            return list(papers)
    
    async def _process_batch(self, papers: List[Paper], extractor: CitationExtractor) -> List[Dict]:
        """Process papers sequentially with delay between each request to avoid rate limits."""
        results = []
        
        for idx, paper in enumerate(papers):
            result = await extractor.get_citations_and_references(paper.arxiv_id)
            results.append(result)
            
            if idx < len(papers) - 1:
                await asyncio.sleep(3.5)
        
        return results
    
    def _save_to_db(self, results: List[Dict]):
        """Save citation data to database."""
        with get_sync_session() as session:
            for data in results:
                arxiv_id = data.get("arxiv_id")
                if not arxiv_id:
                    continue
                
                paper = session.execute(
                    select(Paper).where(
                        (Paper.arxiv_id == arxiv_id) | 
                        (Paper.arxiv_id.like(f"{arxiv_id}v%"))
                    )
                ).scalar_one_or_none()
                
                if not paper:
                    self.log.warning(f"⚠️  Paper not found: {arxiv_id}")
                    continue
                
                paper.s2_paper_id = data.get("s2_paper_id")
                paper.citation_count = data.get("citation_count", 0)
                paper.reference_count = data.get("reference_count", 0)
                paper.influential_citation_count = data.get("influential_citation_count", 0)
                paper.references = data.get("references", [])
                paper.cited_by = data.get("cited_by", [])
                paper.last_citation_update = datetime.now(timezone.utc)
                
                self.log.info(
                    f"💾 Saved: {arxiv_id} | "
                    f"refs={len(paper.references or [])} | "
                    f"citations={len(paper.cited_by or [])}"
                )
            
            session.commit()
            self.log.info(f"✅ Saved {len(results)} papers to database")


class FindStaleCitationsOperator(BaseOperator):
    """
    Find papers with stale citation data (not updated recently).
    Used in citation refresh DAG to target papers for re-extraction.
    
    Args:
        min_age_days: Papers with citations older than this are considered stale
        max_papers: Maximum number of papers to return
    """
    
    def __init__(
        self,
        min_age_days: int = 7,
        max_papers: int = 1000,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.min_age_days = min_age_days
        self.max_papers = max_papers
    
    def execute(self, context: Context) -> List[Dict[str, Any]]:
        """Find stale papers and push to XCom."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.min_age_days)
        
        with get_sync_session() as session:
            papers = session.execute(
                select(Paper).where(
                    Paper.is_processed == True,
                    (Paper.last_citation_update < cutoff) | (Paper.last_citation_update == None)
                ).order_by(
                    Paper.citation_count.desc()
                ).limit(self.max_papers)
            ).scalars().all()
            
            paper_data = [
                {
                    "arxiv_id": p.arxiv_id,
                    "title": p.title,
                    "citation_count": p.citation_count,
                    "last_update": p.last_citation_update.isoformat() if p.last_citation_update else None
                }
                for p in papers
            ]
            
            self.log.info(f"🔍 Found {len(paper_data)} stale papers (older than {self.min_age_days} days)")
            return paper_data
