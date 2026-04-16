import os
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_NAME = os.getenv("APP_ENV", "dev")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{_ENV_NAME}"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["dev", "test", "staging", "prod"] = _ENV_NAME 
    log_level: str = "INFO"

    openai_api_key: str = ""

    mcp_http_host: str = "0.0.0.0"
    mcp_http_port: int = 8080

    # Keep legacy single-key support while encouraging key rotation via MCP_API_KEYS.
    mcp_api_key: str = ""
    mcp_api_keys: str = ""

    require_tenant_header: bool = True
    default_tenant_id: str = "tenant-a"

    rate_limit_requests_per_minute: int = 120
    rate_limit_window_seconds: int = 60

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 60

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/mcp_enterprise"
    db_echo_sql: bool = False
    seed_demo_data: bool = True

    rbac_read_roles: str = "viewer,support_agent,support_manager,admin"
    rbac_write_roles: str = "support_manager,admin"

    orders_write_enabled: bool = True

    @computed_field(return_type=set[str])
    @property 
    def allowed_api_keys(self) -> set[str]:
        values: set[str] = set()
        if self.mcp_api_key:
            values.add(self.mcp_api_key.strip())
        if self.mcp_api_keys:
            values.update(v.strip() for v in self.mcp_api_keys.split(",") if v.strip())
        return values

    @computed_field(return_type=set[str])
    @property
    def read_roles(self) -> set[str]:
        return {v.strip() for v in self.rbac_read_roles.split(",") if v.strip()}

    @computed_field(return_type=set[str])
    @property
    def write_roles(self) -> set[str]:
        return {v.strip() for v in self.rbac_write_roles.split(",") if v.strip()}

    @computed_field(return_type=str)
    @property
    def primary_api_key(self) -> str:
        return next(iter(self.allowed_api_keys), "")


settings = Settings()
