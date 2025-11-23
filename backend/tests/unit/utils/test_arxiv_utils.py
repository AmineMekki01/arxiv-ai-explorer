import pytest
from src.utils.arxiv_utils import normalize_arxiv_id, extract_version, is_valid_arxiv_id


@pytest.mark.unit
class TestArxivUtils:
    """Tests for arXiv utility functions."""
    
    def test_normalize_arxiv_id_with_version(self):
        """Test normalizing arXiv ID with version number."""
        assert normalize_arxiv_id("2301.00001v3") == "2301.00001"
        assert normalize_arxiv_id("1234.5678v1") == "1234.5678"
        assert normalize_arxiv_id("2301.00001v10") == "2301.00001"
    
    def test_normalize_arxiv_id_without_version(self):
        """Test normalizing arXiv ID without version number."""
        assert normalize_arxiv_id("2301.00001") == "2301.00001"
        assert normalize_arxiv_id("1234.5678") == "1234.5678"
    
    def test_normalize_arxiv_id_with_prefix(self):
        """Test normalizing arXiv ID with arxiv: prefix."""
        assert normalize_arxiv_id("arxiv:2301.00001") == "2301.00001"
        assert normalize_arxiv_id("arxiv:2301.00001v2") == "2301.00001"
        assert normalize_arxiv_id("ARXIV:2301.00001") == "2301.00001"
    
    def test_normalize_arxiv_id_with_url(self):
        """Test normalizing arXiv ID from URL."""
        assert normalize_arxiv_id("https://arxiv.org/abs/2301.00001") == "2301.00001"
        assert normalize_arxiv_id("https://arxiv.org/abs/2301.00001v3") == "2301.00001"
    
    def test_normalize_arxiv_id_with_whitespace(self):
        """Test normalizing arXiv ID with whitespace."""
        assert normalize_arxiv_id("  2301.00001v3  ") == "2301.00001"
        assert normalize_arxiv_id("\t2301.00001\n") == "2301.00001"
    
    def test_normalize_arxiv_id_none(self):
        """Test normalizing None."""
        assert normalize_arxiv_id(None) is None
    
    def test_normalize_arxiv_id_empty(self):
        """Test normalizing empty string."""
        assert normalize_arxiv_id("") == ""
    
    def test_extract_version_with_version(self):
        """Test extracting version from arXiv ID."""
        assert extract_version("2301.00001v1") == 1
        assert extract_version("2301.00001v3") == 3
        assert extract_version("2301.00001v10") == 10
    
    def test_extract_version_without_version(self):
        """Test extracting version when not specified (defaults to 1)."""
        assert extract_version("2301.00001") == 1
        assert extract_version("1234.5678") == 1
    
    def test_extract_version_none(self):
        """Test extracting version from None."""
        assert extract_version(None) == 1
    
    def test_extract_version_empty(self):
        """Test extracting version from empty string."""
        assert extract_version("") == 1
    
    def test_is_valid_arxiv_id_new_format(self):
        """Test validation of new format arXiv IDs."""
        assert is_valid_arxiv_id("2301.00001") is True
        assert is_valid_arxiv_id("1234.5678") is True
        assert is_valid_arxiv_id("2301.12345") is True
        assert is_valid_arxiv_id("2301.00001v3") is True
    
    def test_is_valid_arxiv_id_old_format(self):
        """Test validation of old format arXiv IDs."""
        assert is_valid_arxiv_id("hep-th/9901001") is True
        assert is_valid_arxiv_id("cs-ai/0012345") is True
    
    def test_is_valid_arxiv_id_with_prefix(self):
        """Test validation with arxiv: prefix."""
        assert is_valid_arxiv_id("arxiv:2301.00001") is True
        assert is_valid_arxiv_id("arxiv:2301.00001v2") is True
    
    def test_is_valid_arxiv_id_invalid(self):
        """Test validation of invalid arXiv IDs."""
        assert is_valid_arxiv_id("") is False
        assert is_valid_arxiv_id(None) is False
        assert is_valid_arxiv_id("invalid") is False
        assert is_valid_arxiv_id("123") is False
        assert is_valid_arxiv_id("abcd.1234") is False
        assert is_valid_arxiv_id("2301") is False
