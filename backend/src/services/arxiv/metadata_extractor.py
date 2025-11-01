"""Metadata extraction service for arXiv papers."""
from __future__ import annotations

import re
import json
from typing import Any, Dict, Optional

from openai import OpenAI, OpenAIError

from src.config import get_settings
from src.core import logger


AFFILIATION_PROMPT = """
    Extract authors and affiliations from the following paper section.
    Return ONLY valid JSON with this structure:

    {{
        "authors": [
            
                "Author Name 1",
                "Author Name 2"
        ],
        "affiliations": [
            
                "Affiliation 1 of Author 1",
                "Affiliation 2 of Author 2"
        ]
        
    }}

    Section:
    {section}
"""

CATEGORY_MAPPING = {
    'cs.AI': 'Artificial Intelligence',
    'cs.AR': 'Hardware Architecture',
    'cs.CC': 'Computational Complexity',
    'cs.CE': 'Computational Engineering, Finance, and Science',
    'cs.CG': 'Computational Geometry',
    'cs.CL': 'Computation and Language (NLP)',
    'cs.CR': 'Cryptography and Security',
    'cs.CV': 'Computer Vision and Pattern Recognition',
    'cs.CY': 'Computers and Society',
    'cs.DB': 'Databases',
    'cs.DC': 'Distributed, Parallel, and Cluster Computing',
    'cs.DL': 'Digital Libraries',
    'cs.DM': 'Discrete Mathematics',
    'cs.DS': 'Data Structures and Algorithms',
    'cs.ET': 'Emerging Technologies',
    'cs.FL': 'Formal Languages and Automata Theory',
    'cs.GL': 'General Literature',
    'cs.GR': 'Graphics',
    'cs.GT': 'Computer Science and Game Theory',
    'cs.HC': 'Human-Computer Interaction',
    'cs.IR': 'Information Retrieval',
    'cs.IT': 'Information Theory',
    'cs.LG': 'Machine Learning',
    'cs.LO': 'Logic in Computer Science',
    'cs.MA': 'Multiagent Systems',
    'cs.MM': 'Multimedia',
    'cs.MS': 'Mathematical Software',
    'cs.NA': 'Numerical Analysis (alias of math.NA)',
    'cs.NE': 'Neural and Evolutionary Computing',
    'cs.NI': 'Networking and Internet Architecture',
    'cs.OH': 'Other Computer Science',
    'cs.OS': 'Operating Systems',
    'cs.PF': 'Performance',
    'cs.PL': 'Programming Languages',
    'cs.RO': 'Robotics',
    'cs.SC': 'Symbolic Computation',
    'cs.SD': 'Sound',
    'cs.SE': 'Software Engineering',
    'cs.SI': 'Social and Information Networks',
    'cs.SY': 'Systems and Control (alias of eess.SY)',
    'stat.ML': 'Machine Learning',
}


class MetadataExtractor:
    """Extractor for enhanced metadata from arXiv papers."""
    
    def __init__(self):
        """Initialize metadata extractor."""
        self.settings = get_settings()
        self._client: Optional[OpenAI] = None
    
    @property
    def client(self) -> OpenAI:
        """Lazy-load OpenAI client."""
        if self._client is None:
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key not configured in settings")
            self._client = OpenAI(
                api_key=self.settings.openai_api_key,
                timeout=self.settings.openai_timeout,
                max_retries=self.settings.openai_max_retries
            )
        return self._client
    
    def _extract_metrics(self, text: str) -> Dict[str, float]:
        """Extract performance metrics and scores."""
        metrics = {}
        
        metric_patterns = [
            # Classification
            (r'(?i)\baccuracy\b\s*(?:of|=|:)?\s*([0-9.]+)%?', 'accuracy'),
            (r'(?i)\btop[- ]?(\d+)\s*accuracy\b\s*(?:=|:)?\s*([0-9.]+)%?', 'top_k_accuracy'),

            # Precision / Recall / F1
            (r'(?i)\bprecision\b\s*(?:=|:)?\s*([0-9.]+)%?', 'precision'),
            (r'(?i)\brecall\b\s*(?:=|:)?\s*([0-9.]+)%?', 'recall'),
            (r'(?i)\bf1(?:[- ]?score)?\b\s*(?:=|:)?\s*([0-9.]+)%?', 'f1'),

            # IR / Ranking
            (r'(?i)\bndcg(?:@\d+)?\b\s*(?:=|:)?\s*([0-9.]+)%?', 'ndcg'),
            (r'(?i)\bmap\b\s*(?:=|:)?\s*([0-9.]+)%?', 'map'),
            (r'(?i)\bmrr\b\s*(?:=|:)?\s*([0-9.]+)%?', 'mrr'),

            # NLP
            (r'(?i)\bbleu\b\s*(?:score)?\s*(?:=|:)?\s*([0-9.]+)', 'bleu'),
            (r'(?i)\brouge(?:[- ]?[LN]|\b)\s*(?:=|:)?\s*([0-9.]+)', 'rouge'),
            (r'(?i)\bperplexity\b\s*(?:=|:)?\s*([0-9.]+)', 'perplexity'),

            # CV
            (r'(?i)\bmAP\b\s*(?:=|:)?\s*([0-9.]+)', 'map'),
            (r'(?i)\bIoU\b\s*(?:=|:)?\s*([0-9.]+)', 'iou'),
            (r'(?i)\bdice\b\s*(?:=|:)?\s*([0-9.]+)', 'dice'),
            (r'(?i)\bpsnr\b\s*(?:=|:)?\s*([0-9.]+)', 'psnr'),
            (r'(?i)\bssim\b\s*(?:=|:)?\s*([0-9.]+)', 'ssim'),
            (r'(?i)\bfid\b\s*(?:=|:)?\s*([0-9.]+)', 'fid'),

            # Regression
            (r'(?i)\bmae\b\s*(?:=|:)?\s*([0-9.]+)', 'mae'),
            (r'(?i)\brmse\b\s*(?:=|:)?\s*([0-9.]+)', 'rmse'),
            (r'(?i)\bmse\b\s*(?:=|:)?\s*([0-9.]+)', 'mse'),

            # Backend / Systems
            (r'(?i)\blatency\b\s*(?:=|:)?\s*([0-9.]+)\s*(ms|s|µs)?', 'latency'),
            (r'(?i)\bthroughput\b\s*(?:=|:)?\s*([0-9.]+)\s*(req/s|rps|qps|tps)?', 'throughput'),
            (r'(?i)\buptime\b\s*(?:=|:)?\s*([0-9.]+)%?', 'uptime'),
            (r'(?i)\bavailability\b\s*(?:=|:)?\s*([0-9.]+)%?', 'availability'),
            (r'(?i)\bcpu\s*usage\b\s*(?:=|:)?\s*([0-9.]+)%?', 'cpu_usage'), 
        ]

        
        for pattern, metric_name in metric_patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    scores = []
                    for match in matches:
                        value = match[0] if isinstance(match, tuple) else match
                        scores.append(float(value))
                    metrics[metric_name] = max(scores)
                except (ValueError, IndexError):
                    continue
        
        return metrics
    
    def _extract_author_institution_info(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract authors and affiliations using OpenAI."""
        try:
            full_text = paper_data.get('_temp_full_text', '')
            abstract_index = re.search(r'\nAbstract\n', full_text)
            
            text_before_abstract = full_text[:abstract_index.start()] if abstract_index else full_text
            
            if not text_before_abstract:
                logger.warning("No text available for extraction")
                return {'author_count': 0, 'authors': [], 'affiliations': []}
            
            title = paper_data.get('title', '')
            if title:
                title_match = re.search(rf'(?i)\b{re.escape(title)}\b', text_before_abstract)
                if title_match:
                    text_before_abstract = text_before_abstract[title_match.end():]
            
            response = self.client.chat.completions.create(
                model=self.settings.metadata_extractor_model,
                messages=[
                    {"role": "system", "content": AFFILIATION_PROMPT.format(section=text_before_abstract)},
                    {"role": "user", "content": text_before_abstract}
                ]
            )
            
            response_text = response.choices[0].message.content
            data = json.loads(response_text)
            
            authors = data.get('authors', [])
            affiliations = data.get('affiliations', [])
            
            return {
                'author_count': len(authors),
                'authors': authors,
                'affiliations': affiliations
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from OpenAI response: {e}")
            return {'author_count': 0, 'authors': [], 'affiliations': []}
        except OpenAIError as e:
            logger.error(f"OpenAI API error during affiliation extraction: {e}")
            return {'author_count': 0, 'authors': [], 'affiliations': []}
        except Exception as e:
            logger.error(f"Unexpected error in affiliation extraction: {e}")
            return {'author_count': 0, 'authors': [], 'affiliations': []}

    
    def _extract_research_area(self, paper_data: Dict[str, Any]) -> str:
        """Determine the primary research area from categories."""
        categories = paper_data.get('categories', [])
        primary_category = paper_data.get('primary_category', '')
        
        if primary_category in CATEGORY_MAPPING:
            return CATEGORY_MAPPING[primary_category]
        
        for cat in categories:
            if cat in CATEGORY_MAPPING:
                return CATEGORY_MAPPING[cat]
        
        return 'Computer Science'
    
    
    async def extract_metadata(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract enhanced metadata from paper data.
        
        Args:
            paper_data: Dictionary containing paper information (title, summary, content, etc.)
        
        Returns:
            Dictionary with enhanced metadata
        """
        logger.info(f"Extracting metadata for paper: {paper_data.get('arxiv_id', 'unknown')}")
        
        try:
            metrics = self._extract_metrics(paper_data["_temp_full_text"])
            author_info = self._extract_author_institution_info(paper_data)
            research_area = self._extract_research_area(paper_data)
            
            categories = paper_data.get('categories', [])
            primary_category = paper_data.get('primary_category', '')
            
            research_areas_all = []
            for code in ([primary_category] if primary_category else []) + categories:
                if code in CATEGORY_MAPPING:
                    name = CATEGORY_MAPPING[code]
                    if name not in research_areas_all:
                        research_areas_all.append(name)
            
            word_count = len(paper_data["_temp_full_text"].split()) if paper_data["_temp_full_text"] else 0

            enhanced_metadata = {
                'metrics': metrics,
                'research_area': research_area,
                'research_areas_all': research_areas_all,
                'word_count': word_count,
                **author_info,
            }
            
            logger.info(f"Extracted metadata: {len(metrics)} metrics, {len(author_info.get('authors', []))} authors")
            
            result = {**paper_data, **enhanced_metadata}
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            return paper_data