from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="ResearchMind")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    secret_key: str = Field(default="")
    algorithm: str = Field(default="HS256")
    access_token_expires_minutes: int = Field(default=30)

    database_url: str = Field(default="")
    database_echo: bool = Field(default=False)

    redis_url: str = Field(default="")
    
    qdrant_host: str = Field(default="")
    qdrant_port: int = Field(default=6333)
    
    neo4j_uri: str = Field(default="")
    neo4j_user: str = Field(default="")
    neo4j_password: str = Field(default="")

    ollama_base_url: str = Field(default="")
    ollama_model: str = Field(default="")

    default_llm_provider: str = Field(default="ollama")

    embedding_model: str = Field(default="")

    arxiv_api_base: str = Field(default="")
    arxiv_daily_limit: int = Field(default=1000)


    papers_storage_path: Path = Field(default="")
    embedddings_storage_path: Path = Field(default="")

    log_level: str = Field(default="INFO")
    log_file: str = Field(default="")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.papers_storage_path.mkdir(parents=True, exist_ok=True)
        self.embedddings_storage_path.mkdir(parents=True, exist_ok=True)
        self.log_file = Path(self.log_file)
    

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
    

