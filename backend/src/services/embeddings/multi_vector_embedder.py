"""Multi-vector embedding service using fastembed for dense and sparse (BM25) embeddings."""
from typing import List, Dict, Any, Tuple
import logging

from fastembed import TextEmbedding, SparseTextEmbedding

logger = logging.getLogger(__name__)


class MultiVectorEmbedder:
    """
    Generate multiple types of embeddings for hybrid search with rank fusion:
    - Dense embeddings: for semantic search
    - Sparse embeddings (BM25): for keyword-based search
    
    Results are combined using rank fusion for optimal retrieval.
    """
    
    def __init__(
        self,
        dense_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        sparse_model: str = "Qdrant/bm25",
    ):
        """
        Initialize the multi-vector embedder.
        
        Args:
            dense_model: Dense embedding model name
            sparse_model: Sparse embedding model name (BM25)
        """
        self.dense_model_name = dense_model
        self.sparse_model_name = sparse_model
        
        self._dense_model = None
        self._sparse_model = None
        
        logger.info(f"MultiVectorEmbedder initialized with models:")
        logger.info(f"  Dense: {dense_model}")
        logger.info(f"  Sparse: {sparse_model}")
    
    @property
    def dense_model(self) -> TextEmbedding:
        """Lazy-load dense embedding model."""
        if self._dense_model is None:
            logger.info(f"Loading dense model: {self.dense_model_name}")
            self._dense_model = TextEmbedding(self.dense_model_name)
        return self._dense_model
    
    @property
    def sparse_model(self) -> SparseTextEmbedding:
        """Lazy-load sparse embedding model."""
        if self._sparse_model is None:
            logger.info(f"Loading sparse model: {self.sparse_model_name}")
            self._sparse_model = SparseTextEmbedding(self.sparse_model_name)
        return self._sparse_model
    
    def get_embedding_dimensions(self) -> Dict[str, Any]:
        """
        Get embedding dimensions for collection configuration.
        
        Returns:
            Dict with dimension info for each embedding type
        """
        sample_text = ["sample"]
        
        dense_emb = list(self.dense_model.embed(sample_text))[0]
        
        return {
            "dense_dim": len(dense_emb),
            "sparse_model": self.sparse_model_name,
        }
    
    def embed_documents(self, texts: List[str]) -> Tuple[List, List]:
        """
        Generate dense and sparse embeddings for documents.
        
        Args:
            texts: List of document texts
            
        Returns:
            Tuple of (dense_embeddings, sparse_embeddings)
        """
        logger.info(f"Generating embeddings for {len(texts)} documents")
        
        logger.info("Generating dense embeddings...")
        dense_embeddings = list(self.dense_model.embed(texts))
        
        logger.info("Generating sparse embeddings (BM25)...")
        sparse_embeddings = list(self.sparse_model.embed(texts))
        
        logger.info(f"Successfully generated all embeddings")
        logger.info(f"  Dense: {len(dense_embeddings)} x {len(dense_embeddings[0]) if dense_embeddings else 0}")
        logger.info(f"  Sparse: {len(sparse_embeddings)} vectors")
        
        return dense_embeddings, sparse_embeddings
    
    def embed_query(self, query: str) -> Dict[str, Any]:
        """
        Generate dense and sparse embeddings for a query.
        
        Args:
            query: Query text
            
        Returns:
            Dict with dense and sparse embeddings
        """
        logger.info(f"Generating query embeddings for: {query[:100]}...")
        
        dense_vector = next(self.dense_model.query_embed(query))
        sparse_vector = next(self.sparse_model.query_embed(query))
        
        return {
            "dense": dense_vector,
            "sparse": sparse_vector,
        }
    
    def get_vector_names(self) -> Dict[str, str]:
        """
        Get the vector names for Qdrant collection configuration.
        
        Returns:
            Dict with vector names for each embedding type
        """
        return {
            "dense": "all-MiniLM-L6-v2",
            "sparse": "bm25",
        }
