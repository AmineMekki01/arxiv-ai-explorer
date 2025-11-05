from __future__ import annotations

import sys
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

sys.path.insert(0, "/opt/airflow")

from src.services.arxiv.client import ArxivClient
from src.services.arxiv.metadata_extractor import MetadataExtractor
from src.database import get_sync_session
from src.models.paper import Paper
from src.config import get_settings
from src.services.chunking.chunker import ChunkingConfig, PaperChunker

from sentence_transformers import SentenceTransformer

settings = get_settings()

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
        self.categories = categories or settings.arxiv_categories
        self.max_results = int(max_results or settings.arxiv_max_results)
        self.since_days = since_days

    def execute(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        client = ArxivClient()        
        papers = []
        for category in self.categories:
            try:
                category_papers = asyncio.run(
                    client.search_papers(
                        query=f"cat:{category}",
                        max_results=self.max_results,
                        start=self.since_days,
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
    Download and parse PDF content using ArxivClient + Docling parser.
    Expects input XCom: list[dict] with paper metadata including pdf_url.
    Returns XCom: list[dict] with added 'content' field containing parsed text.
    """
    @apply_defaults
    def __init__(
        self,
        input_task_id: str,
        download_dir: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.input_task_id = input_task_id
        self.download_dir = Path(download_dir or settings.papers_storage_path)

    def execute(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        ti = context["ti"]
        papers: List[Dict[str, Any]] = ti.xcom_pull(task_ids=self.input_task_id) or []
        
        if not papers:
            self.log.warning("No papers to parse")
            return []

        from src.services.arxiv.client import ArxivClient
        from src.services.pdf_parser.factory import make_pdf_parser_service
        
        arxiv_client = ArxivClient()
        pdf_parser = make_pdf_parser_service()
        
        parsed_papers = []
        
        for paper in papers:
            try:
                arxiv_id = paper.get('arxiv_id')
                pdf_url = paper.get('pdf_url')
                
                if not arxiv_id or not pdf_url:
                    self.log.warning(f"Skipping paper with missing arxiv_id or pdf_url: {paper}")
                    parsed_papers.append(paper)
                    continue
                
                self.log.info(f"Downloading PDF for {arxiv_id}")
                pdf_path = asyncio.run(
                    arxiv_client.download_pdf(
                        pdf_url=pdf_url,
                        download_path=self.download_dir / f"{arxiv_id.replace('/', '_')}.pdf",
                        max_file_size_mb=settings.pdf_parser_max_file_size_mb
                    )
                )
                
                if not pdf_path or not pdf_path.exists():
                    self.log.error(f"Failed to download PDF for {arxiv_id}")
                    parsed_papers.append(paper)
                    continue
                
                self.log.info(f"Parsing PDF for {arxiv_id}")
                docling_doc = asyncio.run(pdf_parser.parse_pdf(pdf_path))
                
                if docling_doc:
                    from src.services.pdf_parser.docling_utils import (
                        serialize_docling_document,
                        extract_full_text,
                        get_document_metadata
                    )
                    
                    paper_with_content = {**paper}
                    paper_with_content['docling_document'] = serialize_docling_document(docling_doc)
                    paper_with_content['_temp_full_text'] = extract_full_text(docling_doc)
                    paper_with_content['is_processed'] = True
                    
                    doc_meta = get_document_metadata(docling_doc)
                    self.log.info(
                        f"Successfully parsed {arxiv_id}: "
                        f"{doc_meta.get('text_count', 0)} text elements, "
                        f"{doc_meta.get('table_count', 0)} tables, "
                        f"{doc_meta.get('picture_count', 0)} pictures"
                    )
                    parsed_papers.append(paper_with_content)
                else:
                    self.log.warning(f"No content extracted from PDF for {arxiv_id}")
                    parsed_papers.append(paper)
                
                pdf_path.unlink(missing_ok=True)
                
            except Exception as e:
                self.log.error(f"Failed to process PDF for {paper.get('arxiv_id', 'unknown')}: {e}")
                parsed_papers.append(paper)
                continue
        
        self.log.info(f"Processed {len(parsed_papers)} papers, {sum(1 for p in parsed_papers if p.get('docling_document')) } successfully parsed")
        return parsed_papers


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
                if paper.get('docling_document'):
                    from src.services.pdf_parser.docling_utils import (
                        deserialize_docling_document,
                        extract_sections_from_docling,
                        extract_full_text
                    )
                    
                    doc = deserialize_docling_document(paper['docling_document'])
                    
                    if not paper.get('_temp_full_text'):
                        paper['_temp_full_text'] = extract_full_text(doc)
                    
                    paper['content'] = paper['_temp_full_text']
                
                metadata = asyncio.run(extractor.extract_metadata(paper))
                paper.update(metadata)
                
                paper.pop('_temp_full_text', None)
                paper.pop('content', None)
                
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
        normalized["arxiv_url"] = sanitize_text(data.get("arxiv_url")) or ""
        normalized["pdf_url"] = sanitize_text(data.get("pdf_url")) or ""
        normalized["doi"] = sanitize_text(data.get("doi")) or ""
        
        normalized["title"] = sanitize_text(data.get("title")) or "Untitled"
        normalized["abstract"] = sanitize_text(data.get("abstract")) or ""
        normalized["authors"] = data.get("authors") or []
        normalized["affiliations"] = data.get("affiliations") or []
        normalized["published_date"] = to_dt(data.get("published")) or datetime.now()
        normalized["updated_date"] = to_dt(data.get("updated"))
        
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
        
        normalized["docling_document"] = data.get("docling_document")
        normalized["embedding_model"] = sanitize_text(data.get("embedding_model"))
        normalized["embedding_vector"] = sanitize_text(data.get("embedding_vector"))
        
        normalized["word_count"] = data.get("word_count")
        normalized["metrics"] = data.get("metrics")

        
        return {k: v for k, v in normalized.items() if v is not None}

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ti = context["ti"]
        papers: List[Dict[str, Any]] = ti.xcom_pull(task_ids=self.input_task_id) or []
        
        self.log.info(f"Processing {len(papers)} papers for persistence")
        if not papers:
            return {"persisted": 0, "skipped": 0, "papers": []}
        
        if not get_sync_session or not Paper:
            self.log.error("Database session or Paper model not available")
            return {"persisted": 0, "skipped": 0, "error": "Database not configured"}
            
        persisted = 0
        skipped = 0
        processed_ids: List[str] = []
        
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
                            processed_ids.append(data.get("arxiv_id"))
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
                            processed_ids.append(data.get("arxiv_id"))
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
                        return {"persisted": 0, "skipped": 0, "papers": [], "error": str(commit_error)}
                
                unique_ids = sorted(set([pid for pid in processed_ids if pid]))
                return {
                    "persisted": persisted,
                    "skipped": skipped,
                    "papers": [{"arxiv_id": aid} for aid in unique_ids]
                }
                
        except Exception as e:
            self.log.error(f"Unexpected error in PersistDBOperator: {e}", exc_info=True)
            return {"persisted": 0, "skipped": 0, "papers": [], "error": str(e)}


class ChunkDocumentsOperator(BaseOperator):
    """Chunk documents using Docling's HybridChunker on DoclingDocument objects."""
    @apply_defaults
    def __init__(
        self,
        input_task_id: str,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.input_task_id = input_task_id
        self.max_tokens = max_tokens

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ti = context["ti"]
        papers: List[Dict[str, Any]] = ti.xcom_pull(task_ids=self.input_task_id) or []

        if not papers:
            self.log.warning("No papers provided to chunk")
            return {"papers": [], "chunks": []}

        try:
            cfg = ChunkingConfig(max_tokens=int(self.max_tokens))
            chunker = PaperChunker(cfg)
        except Exception as e:
            self.log.error(f"Failed to initialize PaperChunker: {e}")
            chunker = PaperChunker()

        all_chunks: List[Dict[str, Any]] = []
        processed = 0
        
        from src.services.pdf_parser.docling_utils import deserialize_docling_document
        
        for p in papers:
            try:
                arxiv_id = p.get('arxiv_id', 'unknown')
                
                if not p.get("docling_document"):
                    self.log.info(f"Skipping paper {arxiv_id} with no docling_document")
                    continue
                
                doc = deserialize_docling_document(p["docling_document"])
                
                chunks = chunker.chunk_paper(doc)
                
                for idx, chunk in enumerate(chunks):           
                    chunk_dict = {
                        "arxiv_id": arxiv_id,
                        "title": p.get("title", ""),
                        "primary_category": p.get("primary_category", ""),
                        "categories": p.get("categories", []),
                        "published_date": p.get("published_date"),
                        "authors": p.get("authors", []),
                        "affiliations": p.get("affiliations", []),
                        "chunk_index": idx,
                        "chunk_text": chunk.text if hasattr(chunk, 'text') else str(chunk),
                        "heading": chunk.meta.headings[0]
                    }
                    all_chunks.append(chunk_dict)
                
                processed += 1
                self.log.info(f"Chunked {arxiv_id} into {len(chunks)} chunks")
                
            except Exception as e:
                self.log.warning(f"Chunking failed for {p.get('arxiv_id', 'unknown')}: {e}", exc_info=True)
                continue

        self.log.info(f"Chunked {processed} papers into {len(all_chunks)} chunks (max_tokens={self.max_tokens})")
        
        return {
            "papers": papers,
            "chunks": all_chunks
        }

class GenerateEmbeddingsOperator(BaseOperator):
    """
    Generate embeddings for chunks.
    Supports both single-vector (SentenceTransformers) and multi-vector (fastembed) modes.
    Expects input XCom: { 'papers': List[Dict], 'chunks': List[Dict] }
    Returns the same structure with 'vector' or 'vectors' added to each chunk.
    """
    @apply_defaults
    def __init__(
        self,
        input_task_id: str,
        model_name: Optional[str] = None,
        batch_size: int = 64,
        use_multi_vector: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.input_task_id = input_task_id
        self.model_name = model_name or settings.embedding_model_local
        self.batch_size = batch_size
        self.use_multi_vector = use_multi_vector

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ti = context["ti"]
        payload: Dict[str, Any] = ti.xcom_pull(task_ids=self.input_task_id) or {}
        papers: List[Dict[str, Any]] = payload.get("papers") or []
        chunks: List[Dict[str, Any]] = payload.get("chunks") or []

        if not chunks:
            self.log.warning("No chunks to embed")
            return {"papers": papers, "chunks": []}

        valid_chunks = []
        valid_texts = []
        for chunk in chunks:
            text = chunk.get("chunk_text", "")
            if text and isinstance(text, str) and len(text.strip()) > 0:
                valid_chunks.append(chunk)
                valid_texts.append(text.strip())
            else:
                self.log.warning(f"Skipping empty chunk: {chunk.get('arxiv_id', 'unknown')}")
        
        if not valid_chunks:
            self.log.warning("No valid chunks to embed after filtering")
            return {"papers": papers, "chunks": []}
        
        self.log.info(f"Embedding {len(valid_chunks)} valid chunks (filtered out {len(chunks) - len(valid_chunks)} empty chunks)")
        
        if self.use_multi_vector:
            self.log.info("Generating hybrid embeddings (dense + sparse BM25)")
            from src.services.embeddings import MultiVectorEmbedder
            
            embedder = MultiVectorEmbedder()
            dense_embs, sparse_embs = embedder.embed_documents(valid_texts)
            
            self.log.info(f"Generated {len(dense_embs)} sets of hybrid embeddings")
            
            def _to_jsonable(obj):
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                if isinstance(obj, np.generic):
                    return obj.item()
                if isinstance(obj, dict):
                    return {k: _to_jsonable(v) for k, v in obj.items()}
                if isinstance(obj, (list, tuple)):
                    return [_to_jsonable(v) for v in obj]
                return obj

            for i, (dense, sparse) in enumerate(zip(dense_embs, sparse_embs)):
                sparse_dict = sparse.as_object()
                dense_json = _to_jsonable(dense)
                sparse_json = _to_jsonable(sparse_dict)
                
                valid_chunks[i]["vectors"] = {
                    "dense": dense_json,
                    "sparse": sparse_json,
                }
                valid_chunks[i]["embedding_model"] = "hybrid (dense + BM25)"
        else:
            self.log.info(f"Loading single embedding model: {self.model_name}")
            model = SentenceTransformer(self.model_name)
            
            self.log.info(f"Encoding {len(valid_texts)} chunks with batch_size={self.batch_size}")
            vectors = model.encode(valid_texts, batch_size=self.batch_size, show_progress_bar=False, convert_to_numpy=True)
            
            dim = vectors.shape[1] if hasattr(vectors, "shape") and len(vectors.shape) == 2 else None
            self.log.info(f"Generated embeddings with dimension={dim}")
            
            for i, vec in enumerate(vectors):
                try:
                    vec_json = vec.tolist()
                except Exception:
                    vec_json = vec
                valid_chunks[i]["vector"] = vec_json
                valid_chunks[i]["embedding_model"] = self.model_name

        result = {
            "papers": papers,
            "chunks": valid_chunks
        }
        return result


class LoadPapersForEmbeddingOperator(BaseOperator):
    """
    Load papers from PostgreSQL that need embeddings (is_embedded=False) and have full_text.
    Returns XCom: List[Dict[str, Any]] compatible with ChunkDocumentsOperator input.
    """
    @apply_defaults
    def __init__(
        self,
        max_papers: int = 1,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.max_papers = max_papers

    def execute(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not get_sync_session or not Paper:
            self.log.error("Database not configured")
            return []

        results: List[Dict[str, Any]] = []
        with get_sync_session() as session:
            q = (
                session.query(Paper)
                .filter(Paper.is_embedded == False)
                .filter(Paper.docling_document.isnot(None))
            )
            papers = q.limit(self.max_papers).all()
            for p in papers:
                self.log.info(f"Processing paper {p.arxiv_id} (published: {p.published_date})")
                try:
                    results.append({
                        "arxiv_id": p.arxiv_id,
                        "title": p.title,
                        "authors": p.authors or [],
                        "categories": p.categories or [],
                        "primary_category": p.primary_category,
                        "published_date": p.published_date if p.published_date else None,
                        "docling_document": p.docling_document,
                        "affiliations": p.affiliations,
                    })
                except Exception as e:
                    self.log.warning(f"Failed to map paper {getattr(p, 'arxiv_id', 'unknown')}: {e}")

        self.log.info(f"Loaded {len(results)} papers for embedding")
        return results


class MarkPapersEmbeddedOperator(BaseOperator):
    """
    Mark provided arxiv_ids as embedded in PostgreSQL.
    Expects input XCom to contain either a list of papers or a dict with 'papers'.
    """
    @apply_defaults
    def __init__(self, input_task_id: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.input_task_id = input_task_id

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ti = context["ti"]
        payload = ti.xcom_pull(task_ids=self.input_task_id) or []
        if isinstance(payload, dict):
            papers = payload.get("papers") or []
        else:
            papers = payload
        arxiv_ids = {p.get("arxiv_id") for p in papers if p.get("arxiv_id")}

        if not arxiv_ids:
            self.log.info("No papers to mark as embedded")
            return {"updated": 0}

        updated = 0
        with get_sync_session() as session:
            try:
                db_papers = session.query(Paper).filter(Paper.arxiv_id.in_(list(arxiv_ids))).all()
                for dp in db_papers:
                    dp.is_embedded = True
                    dp.is_processed = True
                session.commit()
                updated = len(db_papers)
            except Exception as e:
                self.log.error(f"Failed to mark papers embedded: {e}")
                session.rollback()
                return {"updated": 0, "error": str(e)}

        self.log.info(f"Marked {updated} papers as embedded")
        return {"updated": updated}