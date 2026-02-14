"""Central configuration management for Data Librarian."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Databricks Configuration
    DATABRICKS_HOST: str = os.getenv("DATABRICKS_HOST", "")
    DATABRICKS_TOKEN: str = os.getenv("DATABRICKS_TOKEN", "")

    # LLM Provider Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "local")  # openai, databricks, or local
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Embedding Configuration
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )

    # Retrieval Settings
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "5"))

    # Data Storage
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data"))

    @classmethod
    def validate(cls) -> bool:
        """Validate required settings."""
        if not cls.DATABRICKS_HOST:
            raise ValueError("DATABRICKS_HOST is required")
        if not cls.DATABRICKS_TOKEN:
            raise ValueError("DATABRICKS_TOKEN is required")
        return True

    @classmethod
    def get_metadata_db_path(cls) -> Path:
        """Get path to metadata database."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        return cls.DATA_DIR / "metadata.db"

    @classmethod
    def get_vector_store_path(cls) -> Path:
        """Get path to vector store directory."""
        path = cls.DATA_DIR / "vector_store"
        path.mkdir(parents=True, exist_ok=True)
        return path


# Singleton instance
settings = Settings()
