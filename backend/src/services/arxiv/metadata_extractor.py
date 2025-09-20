from __future__ import annotations

import re
from typing import Any, Dict, List

from src.core import logger


class MetadataExtractor:
    """Extractor for enhanced metadata from arXiv papers."""
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
                    scores = [float(match) for match in matches]
                    metrics[metric_name] = max(scores)
                except ValueError:
                    continue
        
        return metrics
    
    def _extract_author_info(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and enhance author information."""
        authors = paper_data.get('authors', [])
        if not authors:
            return {}
        
        text = paper_data.get('content', '') or paper_data.get('abstract', '')

        pre_abstract_text = text
        m = re.search(r'(?i)\babstract\b', text)
        if m:
            pre_abstract_text = text[: m.start()]

        if pre_abstract_text:
            words = pre_abstract_text.split()
            if len(words) > 1000:
                pre_abstract_text = " ".join(words[:1000])
        

        institution_patterns = [
            r'(?i)\b([A-Z][A-Za-z&\.\'-]+(?:\s+[A-Z][A-Za-z&\.\'-]+)*\s+University)\b',
            r'(?i)\b([A-Z][A-Za-z&\.\'-]+(?:\s+[A-Z][A-Za-z&\.\'-]+)*\s+Institute(?:\s+of\s+Technology)?)\b',
            r'(?i)\b([A-Z][A-Za-z&\.\'-]+(?:\s+[A-Z][A-Za-z&\.\'-]+)*\s+College)\b',
            r'(?i)\b([A-Z][A-Za-z&\.\'-]+(?:\s+[A-Z][A-Za-z&\.\'-]+)*\s+Academy)\b',
            r'(?i)\b((?:University|Institute(?:\s+of\s+Technology)?|College|Academy)\s+of\s+[A-Z][A-Za-z&\.\'-]+(?:\s+[A-Z][A-Za-z&\.\'-]+)*)\b',
            r'(?i)\b([A-Za-z][A-Za-z\s,&\.\'-]*Affiliation(?:s)?)\b',
            r'(?i)\b(MIT|Stanford|Harvard|Berkeley|CMU|Google|Microsoft|Facebook|OpenAI|DeepMind)\b',
        ]
        
        institutions = set()
        for pattern in institution_patterns:
            matches = re.findall(pattern, pre_abstract_text)
            institutions.update(matches)
        
        return {
            'author_count': len(authors),
            'authors': authors,
            'institutions': list(institutions)[:5],
        }

    
    def _extract_research_area(self, paper_data: Dict[str, Any]) -> str:
        """Determine the primary research area."""
        categories = paper_data.get('categories', [])
        primary_category = paper_data.get('primary_category', '')
        
        category_mapping = {
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
        
        if primary_category in category_mapping:
            return category_mapping[primary_category]
        
        for cat in categories:
            if cat in category_mapping:
                return category_mapping[cat]
        
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
        
        content = paper_data.get('content', '')
        title = paper_data.get('title', '')
        abstract = paper_data.get('abstract', '')
        
        full_text = f"{title}\n{abstract}\n{content}"
        
        try:
            metrics = self._extract_metrics(full_text)
            author_info = self._extract_author_info(paper_data)
            research_area = self._extract_research_area(paper_data)
            categories = paper_data.get('categories', [])
            primary_category = paper_data.get('primary_category', '')
            category_mapping = {
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
            research_areas_all = []
            for code in ([primary_category] if primary_category else []) + categories:
                if code in category_mapping:
                    name = category_mapping[code]
                    if name not in research_areas_all:
                        research_areas_all.append(name)
            
            word_count = len(full_text.split()) if full_text else 0
            
            enhanced_metadata = {
                'metrics': metrics,
                'research_area': research_area,
                'research_areas_all': research_areas_all,
                'word_count': word_count,
                **author_info,
            }
            
            logger.info(f"Extracted metadata: {len(metrics)} metrics")
            
            result = {**paper_data, **enhanced_metadata}
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            return paper_data