from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    base_url: str = "http://localhost:11434/v1"
    model_name: str = "deepseek-coder-v2:16b-lite-instruct"
    openai_api_key: str = "ollama"
    embedding_backend: str = "sentence-transformers"
    embedding_model: str = "BAAI/bge-m3"
    vectordb_path: Path = Path("data/vectordb")
    raw_data_path: Path = Path("data/raw")
    retrieval_top_k: int = 6
    request_timeout_seconds: int = 120
    max_output_tokens: int = 512

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
