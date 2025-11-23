import pytest
from src.config import Settings, get_settings


@pytest.mark.unit
class TestSettings:
    """Tests for the Settings configuration class."""

    def test_parse_arxiv_categories_from_string(self, tmp_path, monkeypatch):
        """String arxiv_categories should be split into a list of stripped codes."""
        monkeypatch.setenv("PAPERS_STORAGE_PATH", str(tmp_path / "papers"))
        monkeypatch.setenv("EMBEDDING_STORAGE_PATH", str(tmp_path / "embeddings"))
        monkeypatch.setenv("CONVERSATIONS_STORAGE_PATH", str(tmp_path / "conversations"))
        monkeypatch.setenv("LOG_FILE", str(tmp_path / "logs" / "app.log"))

        settings = Settings(arxiv_categories="cs.AI, cs.LG , cs.CL  ")

        assert settings.arxiv_categories == ["cs.AI", "cs.LG", "cs.CL"]

    def test_parse_arxiv_categories_default_when_empty(self, tmp_path, monkeypatch):
        """Explicit empty arxiv_categories string should yield empty list."""
        monkeypatch.setenv("PAPERS_STORAGE_PATH", str(tmp_path / "papers"))
        monkeypatch.setenv("EMBEDDING_STORAGE_PATH", str(tmp_path / "embeddings"))
        monkeypatch.setenv("CONVERSATIONS_STORAGE_PATH", str(tmp_path / "conversations"))
        monkeypatch.setenv("LOG_FILE", str(tmp_path / "logs" / "app.log"))

        settings = Settings(arxiv_categories="")
        assert settings.arxiv_categories == []

    def test_settings_creates_directories(self, tmp_path, monkeypatch):
        """Settings __init__ should create storage and log directories."""
        papers_dir = tmp_path / "papers"
        embeds_dir = tmp_path / "embeddings"
        conv_dir = tmp_path / "conversations"
        log_file = tmp_path / "logs" / "app.log"

        monkeypatch.setenv("PAPERS_STORAGE_PATH", str(papers_dir))
        monkeypatch.setenv("EMBEDDING_STORAGE_PATH", str(embeds_dir))
        monkeypatch.setenv("CONVERSATIONS_STORAGE_PATH", str(conv_dir))
        monkeypatch.setenv("LOG_FILE", str(log_file))

        settings = Settings()

        assert settings.papers_storage_path.is_dir()
        assert settings.embedding_storage_path.is_dir()
        assert settings.conversations_storage_path.is_dir()
        assert settings.log_file.parent.is_dir()


def test_get_settings_cached_instance():
    """get_settings should return a cached singleton Settings instance."""
    s1 = get_settings()
    s2 = get_settings()

    assert s1 is s2
