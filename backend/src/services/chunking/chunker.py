from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

from docling.chunking import HybridChunker


@dataclass
class ChunkingConfig:
    max_tokens: int = 600
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    merge_peers: bool = True


class PaperChunker:
    """
    Generic chunker for docling documents.
    """

    def __init__(self, config: Optional[ChunkingConfig] = None) -> None:
        self.config = config or ChunkingConfig()
        
        self.tokenizer = HuggingFaceTokenizer(
            tokenizer=AutoTokenizer.from_pretrained(self.config.embedding_model),
            max_tokens=self.config.max_tokens,
        )
        self.chunker = HybridChunker(
            tokenizer=self.tokenizer,
            merge_peers=self.config.merge_peers,

        )

    def chunk_paper(self, docling_document) -> List[Dict]:
        """Chunk a docling document into chunks."""
        chunk_iter = self.chunker.chunk(dl_doc=docling_document)
        return list(chunk_iter)
