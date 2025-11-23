import pytest
from unittest.mock import MagicMock, patch
from src.services.embeddings.multi_vector_embedder import MultiVectorEmbedder


@pytest.mark.unit
class TestMultiVectorEmbedder:
    """Tests for the MultiVectorEmbedder service."""
    
    def test_embedder_initialization(self):
        """Test embedder initialization with default models."""
        embedder = MultiVectorEmbedder()
        
        assert embedder.dense_model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert embedder.sparse_model_name == "Qdrant/bm25"
        assert embedder._dense_model is None
        assert embedder._sparse_model is None
    
    def test_embedder_custom_models(self):
        """Test embedder with custom model names."""
        embedder = MultiVectorEmbedder(
            dense_model="custom/dense-model",
            sparse_model="custom/sparse-model"
        )
        
        assert embedder.dense_model_name == "custom/dense-model"
        assert embedder.sparse_model_name == "custom/sparse-model"
    
    @patch('src.services.embeddings.multi_vector_embedder.TextEmbedding')
    def test_dense_model_lazy_loading(self, mock_text_embedding):
        """Test that dense model is lazy-loaded."""
        embedder = MultiVectorEmbedder()
        
        assert embedder._dense_model is None
        
        _ = embedder.dense_model
        
        mock_text_embedding.assert_called_once_with(
 "sentence-transformers/all-MiniLM-L6-v2"
        )
    
    @patch('src.services.embeddings.multi_vector_embedder.SparseTextEmbedding')
    def test_sparse_model_lazy_loading(self, mock_sparse_embedding):
        """Test that sparse model is lazy-loaded."""
        embedder = MultiVectorEmbedder()
        
        assert embedder._sparse_model is None
        
        _ = embedder.sparse_model
        
        mock_sparse_embedding.assert_called_once_with("Qdrant/bm25")
    
    @patch('src.services.embeddings.multi_vector_embedder.TextEmbedding')
    @patch('src.services.embeddings.multi_vector_embedder.SparseTextEmbedding')
    def test_get_embedding_dimensions(self, mock_sparse, mock_dense):
        """Test getting embedding dimensions."""
        mock_dense_instance = MagicMock()
        mock_dense_instance.embed.return_value = [[0.1] * 384]
        mock_dense.return_value = mock_dense_instance
        
        embedder = MultiVectorEmbedder()
        dimensions = embedder.get_embedding_dimensions()
        
        assert "dense_dim" in dimensions
        assert dimensions["dense_dim"] == 384
        assert dimensions["sparse_model"] == "Qdrant/bm25"
    
    @patch('src.services.embeddings.multi_vector_embedder.TextEmbedding')
    @patch('src.services.embeddings.multi_vector_embedder.SparseTextEmbedding')
    def test_embed_documents(self, mock_sparse, mock_dense):
        """Test embedding multiple documents."""
        mock_dense_instance = MagicMock()
        mock_dense_instance.embed.return_value = [
            [0.1] * 384,
            [0.2] * 384,
        ]
        mock_dense.return_value = mock_dense_instance
        
        mock_sparse_instance = MagicMock()
        mock_sparse_instance.embed.return_value = [
            {"indices": [1, 2], "values": [0.5, 0.3]},
            {"indices": [3, 4], "values": [0.6, 0.4]},
        ]
        mock_sparse.return_value = mock_sparse_instance
        
        embedder = MultiVectorEmbedder()
        texts = ["Document 1", "Document 2"]
        
        dense_emb, sparse_emb = embedder.embed_documents(texts)
        
        assert len(dense_emb) == 2
        assert len(sparse_emb) == 2
        assert len(dense_emb[0]) == 384
    
    @patch('src.services.embeddings.multi_vector_embedder.TextEmbedding')
    @patch('src.services.embeddings.multi_vector_embedder.SparseTextEmbedding')
    def test_embed_query(self, mock_sparse, mock_dense):
        """Test embedding a single query."""
        mock_dense_instance = MagicMock()
        mock_dense_instance.query_embed.return_value = iter([[0.1] * 384])
        mock_dense.return_value = mock_dense_instance
        
        mock_sparse_instance = MagicMock()
        mock_sparse_instance.query_embed.return_value = iter([
            {"indices": [1, 2, 3], "values": [0.5, 0.3, 0.2]}
        ])
        mock_sparse.return_value = mock_sparse_instance
        
        embedder = MultiVectorEmbedder()
        result = embedder.embed_query("test query")
        
        assert "dense" in result
        assert "sparse" in result
        assert len(result["dense"]) == 384
        assert "indices" in result["sparse"]
    
    def test_get_vector_names(self):
        """Test getting vector configuration names."""
        embedder = MultiVectorEmbedder()
        names = embedder.get_vector_names()
        
        assert names["dense"] == "all-MiniLM-L6-v2"
        assert names["sparse"] == "bm25"
    
    @patch('src.services.embeddings.multi_vector_embedder.MultiVectorEmbedder')
    def test_get_shared_embedder_singleton(self, mock_embedder_class):
        """Test that get_shared_embedder returns singleton."""
        from src.services.embeddings.multi_vector_embedder import get_shared_embedder
        import src.services.embeddings.multi_vector_embedder as emb_module
        emb_module._shared_embedder = None
        
        embedder1 = get_shared_embedder()
        embedder2 = get_shared_embedder()
        
        assert embedder1 is embedder2
