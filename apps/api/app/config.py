from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_API_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _API_ROOT.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(
            _API_ROOT / ".env",
            _API_ROOT / ".env.local",
            _REPO_ROOT / ".env",
            _REPO_ROOT / ".env.local",
        ),
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
    tws_connect_timeout_seconds: float = Field(default=8.0)
    tws_enabled: bool = Field(default=False)

    # MH-46B-1: scheduled P&L snapshot cadence (ingestion-only)
    pnl_snapshot_scheduler_enabled: bool = Field(default=False)
    pnl_snapshot_interval_seconds: int = Field(default=60)

    # Auto-paper controlled-run gates (default OFF; only allow when all are satisfied)
    auto_paper_enabled: bool = Field(default=False)
    auto_paper_max_orders_per_run: int = Field(default=50)
    auto_paper_max_orders_per_day: int = Field(default=1000)
    auto_paper_max_notional_usd: float = Field(default=1000000.0)
    auto_paper_symbol_allowlist: str = Field(default="")
    auto_paper_order_type: str = Field(default="LIMIT")
    auto_paper_limit_price: float = Field(default=50.00)
    auto_paper_require_tws: bool = Field(default=True)

    # Background auto-paper scheduler (default OFF; cron path stays the fallback).
    # When enabled, the lifespan registers an IntervalTrigger every
    # AUTO_PAPER_MINUTES_BETWEEN_RUNS minutes instead of the cron schedule.
    # Live trading remains locked regardless of these flags.
    auto_paper_background_scheduler_enabled: bool = Field(default=False)
    auto_paper_minutes_between_runs: int = Field(default=30)
    auto_paper_max_open_positions: int = Field(default=200)
    auto_paper_kill_on_error_count: int = Field(default=3)
    auto_paper_kill_on_reject_rate: float = Field(default=0.5)

    # Automatic historical import loop (disabled by default; opt-in for unattended mode).
    auto_history_import_enabled: bool = Field(default=False)
    auto_history_import_minutes_between_runs: int = Field(default=180)
    auto_history_import_requested_years: int = Field(default=3)
    auto_history_import_provider: str = Field(default="yfinance")
    auto_history_import_timeframes: str = Field(default="1d")

    # Signal sweep cadence (seconds). Slower providers should use >= 60s.
    signal_sweep_interval_seconds: int = Field(default=120)

    # Automatic learning trainer loop (disabled by default; opt-in for unattended model updates).
    auto_learning_enabled: bool = Field(default=False)
    auto_learning_minutes_between_runs: int = Field(default=360)
    auto_learning_min_total_outcomes: int = Field(default=30)
    auto_learning_min_new_outcomes: int = Field(default=10)
    auto_learning_min_hours_between_versions: int = Field(default=6)

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
