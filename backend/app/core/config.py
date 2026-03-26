"""
Core configuration using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    # Database
    neon_database_url: str = "postgresql://postgres:password@localhost/text2sql"

    # Groq
    groq_api_key: str = "your_groq_key"
    groq_model: str = "llama3-70b-8192"

    # App
    app_env: str = "development"
    debug: bool = True
    cors_origins: str = '["http://localhost:3000","http://127.0.0.1:5500","http://localhost:8080","*"]'

    # Paths
    embeddings_path: str = "../data/schema_embeddings.npy"
    schema_metadata_path: str = "../data/schema_metadata.json"

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.cors_origins)
        except Exception:
            return ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()