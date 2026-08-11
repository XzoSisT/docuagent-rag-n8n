"""Environment-based application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables or a local .env file."""

    app_name: str = "DocuAgent RAG API"
    log_level: str = "INFO"

    embedding_provider: Literal["ollama", "openai"] = "ollama"

    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "embeddinggemma"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "docuagent"

    top_k: int = Field(default=4, gt=0)
    min_relevance_score: float = Field(default=0.42, ge=-1.0, le=1.0)
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=200, ge=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_chunk_overlap(self) -> "Settings":
        """Ensure chunking can always move forward."""

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self


@lru_cache
def get_settings() -> Settings:
    """Create settings once and reuse them for the application lifetime."""

    return Settings()
