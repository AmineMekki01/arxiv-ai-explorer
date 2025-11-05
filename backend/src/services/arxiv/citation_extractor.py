"""
Citation extraction from Semantic Scholar API.
Uses 3-call strategy: resolve paperId, then fetch references and citations separately with pagination.
"""
import re
import asyncio
from typing import Dict, List, Optional
import httpx
from src.core import logger
from src.config import get_settings

settings = get_settings()

def normalize_arxiv_id(raw: str) -> Optional[str]:
    """Normalize arXiv ID: strip URL and version suffix."""
    if not raw:
        return None
    m = re.search(r'(\d{4}\.\d{4,5})(?:v\d+)?', raw)
    return m.group(1) if m else None


class CitationExtractor:
    """Extract citations and references from Semantic Scholar."""
    
    def __init__(self):
        """Initialize with optional Semantic Scholar API key for higher rate limits."""
        headers = {"x-api-key": settings.s2_api_key} if settings.s2_api_key else {}
        self.client = httpx.AsyncClient(timeout=30.0, headers=headers)
    
    async def _s2_get(self, url: str, params: dict, max_retries: int = 3) -> dict:
        """Make request with exponential backoff for rate limits and transient errors."""
        import random
        
        for attempt in range(max_retries + 1):
            r = await self.client.get(url, params=params)
            
            if r.status_code == 200:
                return r.json()
            
            if r.status_code in (429, 500, 502, 503):
                if attempt < max_retries:
                    logger.warning(f"S2 API {r.status_code}, retry {attempt + 1}/{max_retries} after {settings.s2_api_delay_time:.1f}s")
                    await asyncio.sleep(settings.s2_api_delay_time)
                    continue
            
            r.raise_for_status()
        
        r.raise_for_status()
        return r.json()
    
    async def _fetch_paper_core(self, arxiv_id: str) -> dict:
        """Fetch paper metadata and counts."""
        fields = "paperId,citationCount,referenceCount,influentialCitationCount,title,externalIds"
        url = f"{settings.s2_base}/paper/arXiv:{arxiv_id}"
        return await self._s2_get(url, {"fields": fields})
    
    async def _fetch_list_paginated(
        self, 
        rel: str,
        paper_id: str, 
        limit: int = 500
    ) -> List[dict]:
        """Fetch references or citations list with pagination."""
        if rel == "references":
            fields = "citedPaper.title,citedPaper.authors,citedPaper.year,citedPaper.externalIds,citedPaper.paperId"
            wrapper_key = "citedPaper"
            edge_fields = []
        elif rel == "citations":
            fields = "citingPaper.title,citingPaper.authors,citingPaper.year,citingPaper.externalIds,citingPaper.paperId,isInfluential"
            wrapper_key = "citingPaper"
            edge_fields = ["isInfluential"]
        else:
            raise ValueError("rel must be 'references' or 'citations'")
        
        url = f"{settings.s2_base}/paper/{paper_id}/{rel}"
        results = []
        offset = 0
        
        while True:
            try:
                data = await self._s2_get(url, {"fields": fields, "limit": limit, "offset": offset})
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400 and limit > 100:
                    limit = 100
                    data = await self._s2_get(url, {"fields": fields, "limit": limit, "offset": offset})
                else:
                    logger.error(f"S2 API error for {rel} of {paper_id}: {e}")
                    break
            
            chunk = data.get("data", []) or []
            for item in chunk:
                paper_obj = item.get(wrapper_key) or {}
                for ef in edge_fields:
                    paper_obj[ef] = item.get(ef, False)
                results.append(paper_obj)
            
            if len(chunk) < limit:
                break
            offset += limit
        
        return results
    
    def _parse_entry(self, e: dict) -> dict:
        """Parse S2 paper object to our schema."""
        ext = e.get("externalIds") or {}
        return {
            "title": e.get("title"),
            "arxiv_id": ext.get("ArXiv"),
            "doi": ext.get("DOI"),
            "year": e.get("year"),
            "authors": [a.get("name") for a in (e.get("authors") or [])][:3],
            "s2_paper_id": e.get("paperId"),
            "is_influential": e.get("isInfluential", False),
        }
    
    async def get_citations_and_references(
        self, 
        arxiv_or_url: str,
        title: str = ""
    ) -> Dict:
        """
        Extract citations and references for an arXiv paper.
        
        Returns dict with:
          - source: "semantic_scholar"
          - arxiv_id: normalized arXiv ID
          - s2_paper_id: Semantic Scholar paper ID
          - citation_count, reference_count, influential_citation_count
          - references: List[dict] - papers this paper cites
          - cited_by: List[dict] - papers that cite this paper
        """
        arxiv_id = normalize_arxiv_id(arxiv_or_url)
        if not arxiv_id:
            raise ValueError(f"Invalid arXiv ID/URL: {arxiv_or_url}")
        
        try:
            core = await self._fetch_paper_core(arxiv_id)
            paper_id = core.get("paperId")
            if not paper_id:
                logger.warning(f"No paperId found for arXiv:{arxiv_id}")
                return self._empty_result(arxiv_id)
            
            refs, cits = await asyncio.gather(
                self._fetch_list_paginated("references", paper_id),
                self._fetch_list_paginated("citations", paper_id),
            )
            
            logger.info(f"✅ Extracted {len(refs)} refs, {len(cits)} citations for {arxiv_id}")
            
            return {
                "source": "semantic_scholar",
                "arxiv_id": arxiv_id,
                "s2_paper_id": paper_id,
                "reference_count": core.get("referenceCount", len(refs)),
                "citation_count": core.get("citationCount", len(cits)),
                "influential_citation_count": core.get("influentialCitationCount", 0),
                "references": [self._parse_entry(e) for e in refs],
                "cited_by": [self._parse_entry(e) for e in cits],
            }
        
        except Exception as e:
            logger.error(f"Failed to extract citations for {arxiv_id}: {e}", exc_info=True)
            return self._empty_result(arxiv_id)
    
    def _empty_result(self, arxiv_id: str) -> dict:
        """Return empty citation result."""
        return {
            "source": "none",
            "arxiv_id": arxiv_id,
            "s2_paper_id": None,
            "reference_count": 0,
            "citation_count": 0,
            "influential_citation_count": 0,
            "references": [],
            "cited_by": [],
        }
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def get_citations_and_references(arxiv_or_url: str, api_key: Optional[str] = None) -> Dict:
    """Extract citations and references for an arXiv paper."""
    extractor = CitationExtractor(api_key=api_key)
    try:
        return await extractor.get_citations_and_references(arxiv_or_url)
    finally:
        await extractor.close()