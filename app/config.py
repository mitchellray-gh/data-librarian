"""Application configuration loaded from environment / .env."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Anything left blank disables that integration gracefully."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Databricks
    databricks_host: str = Field(default="", description="Databricks workspace URL")
    databricks_token: str = Field(default="", description="Databricks PAT or service principal token")
    databricks_catalog: str = Field(default="", description="Unity Catalog catalog name to scan")
    databricks_schema: str = Field(default="", description="Unity Catalog schema name to scan")

    # Claude serving endpoint
    claude_endpoint_url: str = Field(default="", description="URL of the Claude serving endpoint")
    claude_api_key: str = Field(default="", description="Bearer token for the Claude endpoint")
    claude_model: str = Field(default="claude-3-5-sonnet", description="Model identifier")

    # Agent behaviour
    learn_interval_seconds: float = Field(default=15.0, ge=1.0)
    scientist_interval_seconds: float = Field(default=3600.0, ge=1.0)
    sample_row_limit: int = Field(default=20, ge=0, le=1000)
    knowledge_path: str = Field(default="./data/knowledge.json")

    @property
    def databricks_configured(self) -> bool:
        return bool(self.databricks_host and self.databricks_token and self.databricks_catalog and self.databricks_schema)

    @property
    def claude_configured(self) -> bool:
        return bool(self.claude_endpoint_url)

    @property
    def claude_auth_token(self) -> str:
        return self.claude_api_key or self.databricks_token


settings = Settings()
