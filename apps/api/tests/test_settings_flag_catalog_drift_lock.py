"""Drift-lock: Settings safety-flag catalog (cycle 71).

Pins the floor of safety-relevant Settings field names. Renaming
``live_execution_enabled`` to ``live_enabled`` would silently
disconnect ``broker_mode_guard`` from its env switch, leaving the
flag effectively unbound.

Test-only / additive.
"""

from __future__ import annotations

from app.config import Settings

SAFETY_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "live_execution_enabled",
        "broker_mode",
        "broker_provider",
        "ibkr_is_paper",
        "ibkr_account_type",
        "api_key",
    }
)

EXPECTED_FIELDS_FLOOR: int = 28  # current 30; floor allows -2


def _fields() -> frozenset[str]:
    return frozenset(Settings.model_fields.keys())


def test_settings_safety_fields_present() -> None:
    actual = _fields()
    missing = SAFETY_REQUIRED_FIELDS - actual
    assert not missing, (
        f"Settings missing safety-relevant field(s): {sorted(missing)}.\n"
        "These are the env switches that broker_mode_guard and the "
        "auth scheme depend on; their absence makes the safety posture "
        "indeterminate."
    )


def test_settings_field_count_floor() -> None:
    count = len(_fields())
    assert count >= EXPECTED_FIELDS_FLOOR, (
        f"Settings field-count regression: {count} < floor "
        f"{EXPECTED_FIELDS_FLOOR}."
    )


def test_live_execution_enabled_default_off() -> None:
    """``live_execution_enabled`` MUST default to False so that an
    unset env var cannot accidentally arm live trading.
    """
    field = Settings.model_fields["live_execution_enabled"]
    default = field.default
    assert default is False, (
        "live_execution_enabled default is no longer False — "
        f"got {default!r}. This would arm live trading on a fresh "
        "deployment with no env override."
    )
