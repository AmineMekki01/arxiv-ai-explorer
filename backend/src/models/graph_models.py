from typing import List, Optional
from pydantic import BaseModel


class PaperNode(BaseModel):
    """Paper node in the knowledge graph."""
    arxiv_id: str
    title: str
    published_date: Optional[str] = None
    is_external: bool = False


class SimilarPaper(PaperNode):
    """Similar paper with similarity metrics."""
    similarity_score: Optional[float] = None
    shared_concepts: Optional[int] = None
    shared_authors: Optional[int] = None
    shared_citations: Optional[int] = None
    concepts: Optional[List[str]] = None
    authors: Optional[List[str]] = None


class InfluentialPaper(PaperNode):
    """Influential paper with citation metrics."""
    citation_count: int
    category: Optional[str] = None


class CitationNetwork(BaseModel):
    """Citation network around a paper."""
    center_paper: str
    cited_papers: List[PaperNode]
    citing_papers: List[PaperNode]
    depth: int


class ResearchPath(BaseModel):
    """Path between two papers through citations."""
    from_paper: str
    to_paper: str
    path: List[PaperNode]
    length: int


class Collaborator(BaseModel):
    """Author collaborator."""
    collaborator: str
    collaboration_count: int
    shared_papers: List[str]


class TrendingConcept(BaseModel):
    """Trending research concept."""
    concept: str
    paper_count: int
    sample_papers: List[str]




__all__ = [
    "PaperNode",
    "SimilarPaper", 
    "InfluentialPaper",
    "CitationNetwork",
    "ResearchPath",
    "Collaborator",
    "TrendingConcept",
]
