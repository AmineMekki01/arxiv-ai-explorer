from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )

    # app settings
    app_name: str = "ResearchMind"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    database_url: str = ""
    database_echo: bool = False

    # ArXiv
    arxiv_api_base: str = "http://export.arxiv.org/api/query"
    arxiv_daily_limit: int = 1000
    arxiv_max_results: int = 3
    arxiv_categories: List[str] = ["cs.AI", "cs.CL", "cs.LG"]

    # Storage
    papers_storage_path: Path = Path("./data/papers")
    embedding_storage_path: Path = Path("./data/embeddings")

    # Logging
    log_level: str = "INFO"
    log_file: Path = Path("./logs/app.log")

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    
    # Embeddings
    embedding_model_local: str = "all-MiniLM-L6-v2"
    embedding_model_openai: str = "text-embedding-3-small"

    # PDF parser
    pdf_parser_max_pages: int = 150
    pdf_parser_max_file_size_mb: int = 150
    pdf_parser_do_ocr: bool = False
    pdf_parser_do_table_structure: bool = True

    @field_validator('arxiv_categories', mode='before')
    def parse_arxiv_categories(cls, v):
        if isinstance(v, str):
            return [cat.strip() for cat in v.split(',') if cat.strip()]
        return v or ["cs.AI", "cs.CL", "cs.LG"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.papers_storage_path.mkdir(parents=True, exist_ok=True)
        self.embedding_storage_path.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

