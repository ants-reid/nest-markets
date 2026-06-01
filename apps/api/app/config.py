from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Market Hunter API"
    app_env: str = Field(default="development")
    app_debug: bool = Field(default=False)
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")

    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_db: str = Field(default="market_hunter")

    llm_provider: str = Field(default="openai")
    openai_api_key: str = Field(default="")
    openai_model_name: str = Field(default="gpt-4.1-mini")
    openai_timeout: float = Field(default=30.0)
    openai_temperature: float = Field(default=0.0)

    polygon_api_key: str = Field(default="")

    # Security
    api_key: str = Field(default="")  # If empty, auth is disabled (dev mode)
    cors_allowed_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    cors_allowed_origin_regex: str | None = Field(
        default=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    )

    # IBKR Broker Integration (Phase 15)
    ibkr_account_id: str = Field(default="")
    ibkr_gateway_url: str = Field(default="https://localhost:5000/v1/api")
    # Legacy informational flag — NOT read by the adapter or order paths.
    # The authoritative paper/live guards are broker_mode, ibkr_account_type,
    # and live_execution_enabled (see MH-24B broker_mode_guard.py).
    ibkr_is_paper: bool = Field(default=True)
    ibkr_username: str = Field(default="")
    ibkr_password: str = Field(default="")

    # Broker mode isolation (MH-24B)
    # BROKER_PROVIDER — which broker adapter is active (default: ibkr)
    # BROKER_MODE      — "paper" (default) or "live"; live is blocked this phase
    # LIVE_EXECUTION_ENABLED — must stay False; guard rejects True at runtime
    # IBKR_ACCOUNT_TYPE — "paper" (default) or "live"; live is blocked this phase
    broker_provider: str = Field(default="ibkr")
    broker_mode: str = Field(default="paper")
    live_execution_enabled: bool = Field(default=False)
    ibkr_account_type: str = Field(default="paper")

    # TWS / IB Gateway socket adapter (P2 scaffold, read-only).
    # Not routed by default — broker_provider remains "ibkr". These
    # fields exist only so the optional "tws" factory branch can be
    # constructed when a caller explicitly selects it.
    tws_host: str = Field(default="127.0.0.1")
    tws_port: int = Field(default=4002)
    tws_client_id: int = Field(default=43)
    tws_enabled: bool = Field(default=False)

    # MH-46B-1: scheduled P&L snapshot cadence (ingestion-only)
    pnl_snapshot_scheduler_enabled: bool = Field(default=False)
    pnl_snapshot_interval_seconds: int = Field(default=60)

    @property
    def database_url(self) -> str:
        """Return the SQLAlchemy-compatible PostgreSQL connection URL."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
