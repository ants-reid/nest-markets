"""Drift-lock pin: safety-critical default values declared on
``app.config.Settings`` must remain conservative (paper / disabled).

Cycle 64 — MH-DRIFTLOCK-CONFIG-DEFAULTS-CATALOG.

Why this pin exists
-------------------
Cycle 60 pins ORM column defaults; this pin closes the corresponding
configuration surface.  A silent flip of, say, ``live_execution_enabled``
to ``True`` or ``broker_mode`` to ``"live"`` in the Settings class
would arm trading the moment the env var is unset.  Each affected
environment would then be one missing ``.env`` away from live mode.

This test inspects ``Settings.model_fields`` directly (not the live
instance), so any ``.env`` overlay on the developer's machine cannot
mask drift in the source defaults.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

from app.config import Settings

# Hard safety subset: defaults that MUST remain at the conservative
# value on the Settings class itself. Each entry is field_name -> default.
SAFETY_DEFAULT_VALUES: dict[str, object] = {
    "broker_mode": "paper",
    "live_execution_enabled": False,
    "ibkr_is_paper": True,
    "ibkr_account_type": "paper",
    "pnl_snapshot_scheduler_enabled": False,
    "api_key": "",  # empty default => APIKeyAuth disabled in dev only
    "app_env": "development",
    "broker_provider": "ibkr",
}


def _field_default(name: str) -> object:
    fields = Settings.model_fields
    assert name in fields, f"Settings.model_fields has no field {name!r}"
    return fields[name].default


def test_safety_default_values_unchanged() -> None:
    drift: list[str] = []
    for name, expected in SAFETY_DEFAULT_VALUES.items():
        actual = _field_default(name)
        if actual != expected:
            drift.append(
                f"  Settings.{name}: expected default={expected!r}, "
                f"actual={actual!r}"
            )
    assert not drift, (
        "Safety-critical Settings defaults have drifted. These defaults "
        "are the last line of defence when an environment variable is "
        "unset; any flip toward 'live' / True must be reviewed and "
        "recorded in the ledger.\n" + "\n".join(drift)
    )


def test_live_execution_default_must_be_false() -> None:
    """Standalone hard guard for the single most dangerous flag.

    Even if SAFETY_DEFAULT_VALUES is mass-edited, this dedicated test
    keeps the live_execution_enabled assertion isolated and obvious.
    """
    actual = _field_default("live_execution_enabled")
    assert actual is False, (
        f"Settings.live_execution_enabled default is now {actual!r}; "
        "this MUST stay False. Flipping this default would enable live "
        "execution by default in any environment lacking the env var."
    )


def test_broker_mode_default_must_be_paper() -> None:
    """Standalone hard guard mirroring the live-execution check."""
    actual = _field_default("broker_mode")
    assert actual == "paper", (
        f"Settings.broker_mode default is now {actual!r}; "
        "this MUST stay 'paper'. Flipping this default would route "
        "broker traffic to a live venue in any environment lacking "
        "the env var."
    )


def test_settings_field_count_floor() -> None:
    """Floor: catches mass-deletion of Settings fields."""
    field_count = len(Settings.model_fields)
    assert field_count >= 25, (
        f"Settings.model_fields count regressed to {field_count}; "
        "floor is 25. Deleting config fields can mask a default flip "
        "by removing the source of truth entirely."
    )
