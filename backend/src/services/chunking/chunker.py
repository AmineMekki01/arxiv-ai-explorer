from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date

from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.embeddings import SentenceTransformerEmbeddings
from transformers import AutoTokenizer


@dataclass
class ChunkingConfig:
    max_tokens: int = 600
    overlap_tokens: int = 100
    preserve_newlines: bool = True
    semantic_threshold: int = 1000
    embedding_model: str = "all-MiniLM-L6-v2"
    breakpoint_threshold_type: str = "percentile"
    breakpoint_threshold_amount: float = 95.0


class PaperChunker:
    """
    Generic text chunker with simple token approximation (by whitespace words).

    Produces chunk objects expected by downstream embedding and Qdrant upsert:
    - arxiv_id
    - title
    - primary_category
    - categories
    - section_title
    - section_type
    - chunk_index
    - chunk_text
    - start_char
    - end_char
    - total_chunks
    """

    def __init__(self, config: Optional[ChunkingConfig] = None) -> None:
        self.config = config or ChunkingConfig()
        
        self._semantic_chunker = None
        self._hf_tokenizer = None
        try:
            embeddings = SentenceTransformerEmbeddings(model_name=self.config.embedding_model)
            self._semantic_chunker = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type=self.config.breakpoint_threshold_type,
                breakpoint_threshold_amount=self.config.breakpoint_threshold_amount,
            )
        except Exception as e:
            self._semantic_chunker = None
        if AutoTokenizer is not None:
            try:
                self._hf_tokenizer = AutoTokenizer.from_pretrained(self.config.embedding_model)
            except Exception:
                self._hf_tokenizer = None

    def _count_tokens(self, text: str) -> int:
        """Count tokens using the embedding model's tokenizer when available.
        Falls back to whitespace token count if tokenizer is unavailable.
        """
        if self._hf_tokenizer is not None:
            try:
                return len(self._hf_tokenizer.encode(text, add_special_tokens=False))
            except Exception:
                pass
        return len(text.split())


    def _make_chunk(
        self,
        base: Dict,
        section_title: str,
        section_type: str,
        chunk_index: int,
        chunk_text: str,
        start_char: int,
        end_char: int,
        total_chunks: int,
    ) -> Dict:
        """Create chunk with selective metadata for optimal Qdrant performance."""
        pd = base.get("published_date") or base.get("published")
        if isinstance(pd, (datetime, date)):
            try:
                pd = pd.isoformat()
            except Exception:
                pd = str(pd)

        payload = {
            "arxiv_id": base.get("arxiv_id"),
            "title": base.get("title"),
            "primary_category": base.get("primary_category"),
            "categories": base.get("categories") or [],
            "section_title": section_title,
            "section_type": section_type,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "chunk_text": chunk_text,
            "start_char": start_char,
            "end_char": end_char,
            "published_date": pd,
            "authors": base.get("authors", []),
            "word_count": len(chunk_text.split()),
        }
        return payload

    def chunk_section(self, base: Dict, section_title: str, content: str) -> List[Dict]:
        if not content:
            return []

        content_tokens = self._count_tokens(content)
        if content_tokens > self.config.semantic_threshold:
            return self._semantic_chunk_section(base, section_title, content)
        else:
            s_type = section_title or "content"
            chunk_text = content
            start_char = 0
            end_char = len(content)
            single = self._make_chunk(
                base=base,
                section_title=section_title or "content",
                section_type=s_type,
                chunk_index=0,
                chunk_text=chunk_text,
                start_char=start_char,
                end_char=end_char,
                total_chunks=1,
            )
            return [single]

    def _semantic_chunk_section(self, base: Dict, section_title: str, content: str) -> List[Dict]:
        """Semantically chunk large sections using LangChain SemanticChunker."""

        semantic_chunks = self._semantic_chunker.split_text(content)
    
        chunks: List[Dict] = []
        s_type = section_title or "content"
        
        for chunk_idx, chunk_text in enumerate(semantic_chunks):
            start_char = content.find(chunk_text[:50]) if len(chunk_text) > 50 else content.find(chunk_text)
            if start_char == -1:
                start_char = chunk_idx * len(content) // len(semantic_chunks)
            end_char = start_char + len(chunk_text)
            
            chunks.append(
                self._make_chunk(
                    base=base,
                    section_title=section_title or "content",
                    section_type=s_type,
                    chunk_index=chunk_idx,
                    chunk_text=chunk_text,
                    start_char=start_char,
                    end_char=end_char,
                    total_chunks=len(semantic_chunks),
                )
            )
        
        return chunks

    def chunk_paper(self, paper: Dict) -> List[Dict]:
        """Chunk a single paper. Prefer section-aware splitting when available.
        Expects a paper dict with at least 'content' and optionally 'sections'.
        """
        content = (paper.get("content") or "").strip()
        sections = paper.get("sections") or []

        if sections:
            all_chunks: List[Dict] = []
            for _, sec in enumerate(sections):
                title = sec.get("title")
                text = sec.get("content") or ""
                all_chunks.extend(self.chunk_section(paper, title, text))
            if all_chunks:
                return all_chunks

        return self.chunk_section(paper, section_title="content", content=content)

