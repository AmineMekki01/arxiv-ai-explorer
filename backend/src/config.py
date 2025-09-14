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
        env_ignore_empty=True,
    )

    app_name: str = Field(default="ResearchMind")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    database_url: str = Field(default="")
    database_echo: bool = Field(default=False)

    arxiv_api_base: str = Field(default="")
    arxiv_daily_limit: int = Field(default=1000)

    papers_storage_path: Path = Field(default="")

    log_level: str = Field(default="INFO")
    log_file: Path = Field(default=Path("./logs/app.log"))
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.papers_storage_path.mkdir(parents=True, exist_ok=True)
        self.log_file = Path(self.log_file)
    

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
    

