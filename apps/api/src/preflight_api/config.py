from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Agent Preflight Sandbox"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://preflight:preflight@localhost:5432/preflight"
    redis_url: str = "redis://localhost:6379/0"

    temporal_target: str | None = None
    temporal_namespace: str = "default"
    temporal_task_queue: str = "preflight"

    sandbox_api_keys: str = ""
    rate_limit_per_minute: int = 120
    evaluate_cache_ttl_seconds: int = 3600

    litellm_model: str = "xai/grok-3-mini"

    nia_api_key: str | None = None
    nia_base_url: str = "https://apigcp.trynia.ai/v2"

    greptile_api_key: str | None = None
    github_token: str | None = None
    greptile_base_url: str = "https://api.greptile.com/v2"

    allscale_api_key: str | None = None
    allscale_base_url: str = "https://api.allscale.io"


@lru_cache
def get_settings() -> Settings:
    return Settings()
