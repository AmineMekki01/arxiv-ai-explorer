from __future__ import annotations

import re
from typing import Any, Dict, List

from src.core import logger


class MetadataExtractor:
    """Extractor for enhanced metadata from arXiv papers."""
    
    def __init__(self) -> None:
        self.methodology_keywords = {
            'machine learning', 'deep learning', 'neural network', 'transformer',
            'attention mechanism', 'convolutional', 'recurrent', 'lstm', 'gru',
            'reinforcement learning', 'supervised learning', 'unsupervised learning',
            'semi-supervised', 'self-supervised', 'transfer learning', 'fine-tuning',
            'pre-training', 'bert', 'gpt', 'llm', 'language model', 'nlp',
            'computer vision', 'image classification', 'object detection',
            'segmentation', 'generative model', 'gan', 'vae', 'diffusion',
            'optimization', 'gradient descent', 'backpropagation', 'adam',
            'regularization', 'dropout', 'batch normalization', 'layer normalization'
        } # will adapt this 
        
        self.contribution_patterns = [
            r'(?i)we\s+(?:propose|present|introduce|develop|design)',
            r'(?i)our\s+(?:contribution|approach|method|model|framework)',
            r'(?i)(?:novel|new)\s+(?:approach|method|model|framework|technique)',
            r'(?i)(?:first|pioneering)\s+(?:work|study|approach)',
            r'(?i)(?:state-of-the-art|sota)\s+(?:performance|results)',
        ]
        
        self.evaluation_patterns = [
            r'(?i)(?:experiment|evaluation|benchmark|test)\s+(?:on|with|using)',
            r'(?i)(?:dataset|corpus|benchmark):\s*([A-Z][A-Za-z0-9\-_]+)',
            r'(?i)(?:accuracy|precision|recall|f1|bleu|rouge)\s*(?:score|of)?\s*(?::|=)?\s*([0-9.]+)',
        ]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key technical terms and concepts."""
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.methodology_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        capitalized_terms = re.findall(r'\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\b', text)
        
        common_words = {'The', 'This', 'That', 'These', 'Those', 'We', 'Our', 'In', 'On', 'At', 'To', 'For'}
        technical_terms = []
        
        for term in capitalized_terms:
            words = term.split()
            if (2 <= len(words) <= 4 and 
                not any(word in common_words for word in words) and
                len(term) > 4):
                technical_terms.append(term)
        
        all_keywords = list(set(found_keywords + technical_terms))
        return all_keywords[:20]
    
    def _extract_contributions(self, text: str) -> List[str]:
        """Extract stated contributions from the paper."""
        contributions = []
        
        for pattern in self.contribution_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 200)
                context = text[start:end]
                
                sentences = re.split(r'[.!?]', context)
                for sentence in sentences:
                    if match.group().lower() in sentence.lower():
                        clean_sentence = sentence.strip()
                        if len(clean_sentence) > 20:
                            contributions.append(clean_sentence)
                        break
        
        return contributions[:5]
    
    def _extract_datasets(self, text: str) -> List[str]:
        """Extract mentioned datasets and benchmarks."""
        datasets = set()
        
        dataset_patterns = [
            r'(?i)(?:dataset|corpus|benchmark):\s*([A-Z][A-Za-z0-9\-_]+)',
            r'(?i)(?:on|using|with)\s+(?:the\s+)?([A-Z][A-Za-z0-9\-_]+)\s+(?:dataset|corpus|benchmark)',
            r'\b(MNIST|CIFAR|ImageNet|COCO|SQuAD|GLUE|SuperGLUE|WMT|CoNLL|Penn\s+Treebank)\b',
        ]
        
        for pattern in dataset_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                if len(match) > 2:
                    datasets.add(match)
        
        return list(datasets)[:10]
    
    def _extract_metrics(self, text: str) -> Dict[str, float]:
        """Extract performance metrics and scores."""
        metrics = {}
        
        metric_patterns = [
            (r'(?i)accuracy\s*(?:of|:|=)?\s*([0-9.]+)%?', 'accuracy'),
            (r'(?i)precision\s*(?:of|:|=)?\s*([0-9.]+)%?', 'precision'),
            (r'(?i)recall\s*(?:of|:|=)?\s*([0-9.]+)%?', 'recall'),
            (r'(?i)f1\s*(?:score)?\s*(?:of|:|=)?\s*([0-9.]+)%?', 'f1'),
            (r'(?i)bleu\s*(?:score)?\s*(?:of|:|=)?\s*([0-9.]+)%?', 'bleu'),
            (r'(?i)rouge\s*(?:score)?\s*(?:of|:|=)?\s*([0-9.]+)%?', 'rouge'),
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
        
        text = paper_data.get('content', '') or paper_data.get('summary', '')
        
        institution_patterns = [
            r'\b([A-Z][a-z]+\s+University)\b',
            r'\b([A-Z][a-z]+\s+Institute(?:\s+of\s+Technology)?)\b',
            r'\b([A-Z][a-z]+\s+College)\b',
            r'\b(MIT|Stanford|Harvard|Berkeley|CMU|Google|Microsoft|Facebook|OpenAI|DeepMind)\b',
        ]
        
        institutions = set()
        for pattern in institution_patterns:
            matches = re.findall(pattern, text)
            institutions.update(matches)
        
        return {
            'author_count': len(authors),
            'authors': authors[:10],
            'institutions': list(institutions)[:5],
        }
    
    def _analyze_paper_type(self, paper_data: Dict[str, Any]) -> str:
        """Classify the type of paper based on content."""
        text = (paper_data.get('content', '') + ' ' + 
                paper_data.get('title', '') + ' ' + 
                paper_data.get('summary', '')).lower()
        
        if any(term in text for term in ['survey', 'review', 'overview', 'comprehensive']):
            return 'survey'
        elif any(term in text for term in ['dataset', 'corpus', 'benchmark', 'collection']):
            return 'dataset'
        elif any(term in text for term in ['empirical', 'experimental', 'evaluation', 'comparison']):
            return 'empirical'
        elif any(term in text for term in ['theoretical', 'analysis', 'proof', 'theorem']):
            return 'theoretical'
        elif any(term in text for term in ['system', 'framework', 'tool', 'implementation']):
            return 'system'
        else:
            return 'research'
    
    def _extract_research_area(self, paper_data: Dict[str, Any]) -> str:
        """Determine the primary research area."""
        categories = paper_data.get('categories', [])
        primary_category = paper_data.get('primary_category', '')
        
        category_mapping = {
            'cs.AI': 'Artificial Intelligence',
            'cs.LG': 'Machine Learning',
            'cs.CL': 'Natural Language Processing',
            'cs.CV': 'Computer Vision',
            'cs.IR': 'Information Retrieval',
            'cs.RO': 'Robotics',
            'cs.CR': 'Cryptography and Security',
            'cs.DB': 'Databases',
            'cs.DS': 'Data Structures and Algorithms',
            'cs.HC': 'Human-Computer Interaction',
            'cs.NE': 'Neural and Evolutionary Computing',
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
        summary = paper_data.get('summary', '')
        
        full_text = f"{title}\n{summary}\n{content}"
        
        try:
            keywords = self._extract_keywords(full_text)
            contributions = self._extract_contributions(full_text)
            datasets = self._extract_datasets(full_text)
            metrics = self._extract_metrics(full_text)
            author_info = self._extract_author_info(paper_data)
            paper_type = self._analyze_paper_type(paper_data)
            research_area = self._extract_research_area(paper_data)
            
            word_count = len(full_text.split()) if full_text else 0
            
            enhanced_metadata = {
                'keywords': keywords,
                'contributions': contributions,
                'datasets': datasets,
                'metrics': metrics,
                'paper_type': paper_type,
                'research_area': research_area,
                'word_count': word_count,
                **author_info,
            }
            
            logger.info(f"Extracted metadata: {len(keywords)} keywords, {len(contributions)} contributions, {len(datasets)} datasets")
            
            result = {**paper_data, **enhanced_metadata}
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            return paper_data