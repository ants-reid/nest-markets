"""MH-DRIFTLOCK-CORS-DEFAULT-ORIGINS-CATALOG

Pins the default value of ``Settings.cors_allowed_origins`` so an accidental
widening (e.g. to ``"*"``) is caught. Production deployments override via env;
this only guards the in-source default.
"""
from __future__ import annotations

from app.config import Settings

_EXPECTED_DEFAULTS: tuple[str, ...] = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def test_cors_default_origins_exact_catalog(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # Strip any env override so we observe the in-source default.
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    settings = Settings()
    assert tuple(settings.cors_allowed_origins) == _EXPECTED_DEFAULTS


def test_cors_default_origins_no_wildcard(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    settings = Settings()
    assert "*" not in settings.cors_allowed_origins, (
        "Wildcard CORS origin must never be the in-source default"
    )
