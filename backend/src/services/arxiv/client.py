from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core import logger

class ArxivClient:
    """Client for interacting with the arXiv API."""
    
    def __init__(
        self,
        base_url: str = "http://export.arxiv.org/api/query",
        rate_limit: float = 3.0,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.timeout = timeout
        self._last_request_time = 0.0
        
    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        min_interval = 1.0 / self.rate_limit
        
        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)
        
        self._last_request_time = asyncio.get_event_loop().time()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _make_request(self, params: Dict[str, Any]) -> str:
        """Make a rate-limited request to the arXiv API."""
        await self._rate_limit()
        
        url = f"{self.base_url}?{urlencode(params)}"
        logger.info(f"Fetching arXiv data: {url}")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()
    
    def _parse_atom_feed(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse arXiv Atom feed XML into structured data."""
        try:
            root = ET.fromstring(xml_content.encode('utf-8'))
            
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            papers = []
            entries = root.findall('atom:entry', namespaces)
            
            for entry in entries:
                paper = self._parse_entry(entry, namespaces)
                papers.append(paper)
            
            return papers
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse arXiv XML response: {e}")
            return []
            
    def _parse_entry(self, entry: ET.Element, namespaces: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Parse a single entry from the arXiv Atom feed."""
        try:
            id_elem = entry.find('atom:id', namespaces)
            title_elem = entry.find('atom:title', namespaces)
            summary_elem = entry.find('atom:summary', namespaces)
            published_elem = entry.find('atom:published', namespaces)
            updated_elem = entry.find('atom:updated', namespaces)

            arxiv_id = id_elem.text.split('/')[-1] if id_elem.text else ""
            title = re.sub(r'\s+', ' ', title_elem.text.strip()) if title_elem.text else ""
            summary = re.sub(r'\s+', ' ', summary_elem.text.strip()) if summary_elem.text else ""

            authors = []
            for author_elem in entry.findall('atom:author', namespaces):
                name_elem = author_elem.find('atom:name', namespaces)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text.strip())

            categories = [cat.get('term') for cat in entry.findall('atom:category', namespaces) if cat.get('term')]
            primary_category = ""
            primary_cat_elem = entry.find('arxiv:primary_category', namespaces)
            if primary_cat_elem is not None:
                primary_category = primary_cat_elem.get('term', '')

            pdf_url, abs_url = "", ""
            for link_elem in entry.findall('atom:link', namespaces):
                href = link_elem.get('href', '')
                title_attr = link_elem.get('title', '')
                if 'pdf' in title_attr.lower() or href.endswith('.pdf'):
                    pdf_url = href
                elif 'abs' in href or '/abs/' in href:
                    abs_url = href

            published = published_elem.text if published_elem is not None else ""
            updated = updated_elem.text if updated_elem is not None else ""

            doi = ""
            doi_elem = entry.find('arxiv:doi', namespaces)
            if doi_elem is not None and doi_elem.text:
                doi = doi_elem.text.strip()

            journal_ref = ""
            journal_elem = entry.find('arxiv:journal_ref', namespaces)
            if journal_elem is not None and journal_elem.text:
                journal_ref = journal_elem.text.strip()

            return {
                'arxiv_id': arxiv_id,
                'title': title,
                'summary': summary,
                'authors': authors,
                'categories': categories,
                'primary_category': primary_category,
                'published': published,
                'updated': updated,
                'pdf_url': pdf_url,
                'abs_url': abs_url,
                'doi': doi,
                'journal_ref': journal_ref,
            }

        except Exception as e:
            logger.warning(f"Failed to parse entry: {e}")
            return None

    
    async def search_papers(
        self,
        query: str,
        max_results: int = 100,
        start: int = 0,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> List[Dict[str, Any]]:
        """
        Search for papers on arXiv.
        
        Args:
            query: Search query (can include field prefixes like 'cat:cs.AI')
            max_results: Maximum number of results to return
            start: Starting index for pagination
            sort_by: Sort criterion ('relevance', 'lastUpdatedDate', 'submittedDate')
            sort_order: Sort order ('ascending', 'descending')
        
        Returns:
            List of paper dictionaries with metadata
        """
        params = {
            'search_query': query,
            'start': start,
            'max_results': min(max_results, 2000),
            'sortBy': sort_by,
            'sortOrder': sort_order,
        }
        try:
            xml_content = await self._make_request(params)
            papers = self._parse_atom_feed(xml_content)
            return papers
        except Exception as e:
            logger.error(f"Failed to search papers: {e}")
            return []
            
    async def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific paper by its arXiv ID.
        
        Args:
            arxiv_id: arXiv paper ID (e.g., '2301.12345' or 'cs.AI/0601001')
        
        Returns:
            Paper dictionary or None if not found
        """
        clean_id = arxiv_id.replace('arXiv:', '').strip()
        
        papers = await self.search_papers(f"id:{clean_id}", max_results=1)
        return papers[0] if papers else None
    
    async def get_recent_papers(
        self,
        categories: List[str],
        days_back: int = 1,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get recent papers from specified categories.
        
        Args:
            categories: List of arXiv categories (e.g., ['cs.AI', 'cs.LG'])
            days_back: Number of days to look back
            max_results: Maximum number of results
        
        Returns:
            List of recent papers
        """
        cat_queries = [f"cat:{cat}" for cat in categories]
        query = " OR ".join(cat_queries)
        
        papers = await self.search_papers(
            query=query,
            max_results=max_results,
            sort_by="submittedDate",
            sort_order="descending"
        )
        
        if days_back > 0:
            cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).date()
            filtered_papers = []
            
            for paper in papers:
                try:
                    published_str = paper.get('published', '')
                    if published_str:
                        published_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                        if published_date.date() >= cutoff_date:
                            filtered_papers.append(paper)
                except Exception:
                    filtered_papers.append(paper)

            papers = filtered_papers
        
        return papers