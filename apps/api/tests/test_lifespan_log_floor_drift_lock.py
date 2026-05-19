"""Drift-lock pin: operator-visible safety log lines in
``app.main._lifespan``.

Cycle 61 — MH-DRIFTLOCK-LOG-LEVEL-FLOOR.

Why this pin exists
-------------------
At process startup, ``app.main._lifespan`` emits two operator-visible
log lines that form part of the *visible* safety contract:

  * ``BROKER MODE: provider=… mode=… live_execution_enabled=… …``
    (INFO) — operators read this to confirm boot-time posture.
  * ``BROKER SAFETY WARNING: live execution configuration detected at
    startup! …`` (ERROR) — fires when live-execution config is detected.

Silently dropping either line (or downgrading the WARNING from ERROR to
DEBUG) would remove the operator's earliest signal that something is
mis-configured, *without* changing any guard or service code.  This pin
freezes the substrings + the logger levels at which they are emitted.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

import inspect

from app import main as app_main


# (substring, required_logger_method) — the call must appear in
# ``_lifespan`` source AND must be invoked on the exactly-named logger
# method (so an INFO ↔ DEBUG silent downgrade is caught).
EXPECTED_LIFESPAN_LOG_LINES: list[tuple[str, str]] = [
    (
        "BROKER MODE: provider=%s mode=%s live_execution_enabled=%s "
        "paper_trading_enabled=%s",
        "info",
    ),
    (
        "BROKER SAFETY WARNING: live execution configuration detected at "
        "startup!",
        "error",
    ),
    (
        "APScheduler started",
        "info",
    ),
    (
        "Broker tickle job registered (every 55s)",
        "info",
    ),
]


def _lifespan_source() -> str:
    return inspect.getsource(app_main._lifespan)


def test_lifespan_log_floor_substrings_present() -> None:
    """Every safety-floor log substring must appear verbatim in
    ``_lifespan`` source."""
    src = _lifespan_source()
    missing = [s for (s, _) in EXPECTED_LIFESPAN_LOG_LINES if s not in src]
    assert not missing, (
        "Operator-visible safety log lines missing from app.main._lifespan: "
        f"{missing}. These lines form the visible startup safety contract "
        "and may not be silently removed."
    )


def test_lifespan_safety_warning_emitted_at_error_level() -> None:
    """The BROKER SAFETY WARNING line MUST be emitted at ERROR level.

    A silent downgrade to .info()/.warning()/.debug() would hide the
    earliest operator signal that live execution config has leaked in.
    """
    src = _lifespan_source()
    safety_line_substr = (
        "BROKER SAFETY WARNING: live execution configuration detected"
    )
    # Find the safety-warning call site and walk back ~5 lines to find the
    # logger method invocation.
    idx = src.find(safety_line_substr)
    assert idx != -1, "BROKER SAFETY WARNING line not found"
    # Look at ~200 chars before the substring to find the .error( call.
    window = src[max(0, idx - 200): idx]
    assert "_logger.error(" in window, (
        "BROKER SAFETY WARNING is no longer emitted via _logger.error(...). "
        "Downgrading this line below ERROR silently removes the operator's "
        "earliest live-config-leak alarm."
    )


def test_lifespan_broker_mode_line_emitted_at_info_level() -> None:
    """The BROKER MODE startup line MUST remain at INFO level so it shows
    up in default operator log streams."""
    src = _lifespan_source()
    idx = src.find("BROKER MODE: provider=%s mode=%s")
    assert idx != -1, "BROKER MODE startup line not found"
    window = src[max(0, idx - 200): idx]
    assert "_logger.info(" in window, (
        "BROKER MODE startup line is no longer emitted via _logger.info(...). "
        "Downgrading below INFO hides operator-visible boot-time posture."
    )


def test_lifespan_safety_warning_mentions_known_kill_vars() -> None:
    """The safety-warning line must continue to name the env vars an
    operator should check.  Renaming them silently de-couples the alarm
    from the diagnostic action it tells operators to take."""
    src = _lifespan_source()
    required_mentions = (
        "LIVE_EXECUTION_ENABLED",
        "BROKER_MODE",
        "IBKR_ACCOUNT_TYPE",
    )
    missing = [m for m in required_mentions if m not in src]
    assert not missing, (
        f"BROKER SAFETY WARNING no longer mentions: {missing}. "
        "These names are the operator's actionable diagnostic vector and "
        "must remain in the warning text."
    )
