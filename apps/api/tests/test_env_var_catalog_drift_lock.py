"""Drift-lock pin: catalog of environment variables read by ``app/``.

Cycle 60 — MH-DRIFTLOCK-ENV-VAR-CATALOG.

Why this pin exists
-------------------
A new ``os.getenv("LIVE_TRADING_ENABLED")`` (or any rename of an existing
kill-switch-adjacent variable) added without test review would silently
expose runtime trading behaviour to operator-set environment.  This pin
freezes the **set** of env-var keys read across ``app/`` and isolates a
SAFETY_KILL_VARS subset whose key names form part of the safety contract.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

import re
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent / "app"

# Every env var key read anywhere under app/ via os.environ[...] /
# os.environ.get(...) / os.getenv(...).  Keys MUST be ALL_CAPS_SNAKE.
EXPECTED_ENV_VAR_KEYS: set[str] = {
    "APP_ENV",
    "AUDIT_LOG_PATH",
    "FLEX_QUERY_ID",
    "FLEX_TOKEN",
    "PAPER_TRADING_ENABLED",
    "WORKER_RUN_LOG_PATH",
}

# Subset whose presence/absence is part of the safety contract.  Renaming
# any of these silently changes the runtime trading posture without
# touching guard code.
SAFETY_KILL_VARS: set[str] = {
    "APP_ENV",            # gates non-test scheduler startup in app.main
    "PAPER_TRADING_ENABLED",  # gates LiveExecutionService paper enablement
}

# Keys that have historically been associated with live/auto trading.  These
# MUST NOT be read anywhere under app/ until the matrix explicitly unlocks
# them.  A drive-by addition would silently expose live execution to the
# environment.
FORBIDDEN_ENV_VAR_KEYS: set[str] = {
    "LIVE_TRADING_ENABLED",
    "AUTO_TRADING_ENABLED",
    "LIVE_EXECUTION_ENABLED",
    "AUTO_PAPER_ENFORCEMENT_ENABLED",
    "BROKER_ALLOW_LIVE",
    "ENABLE_LIVE_ORDERS",
    "FORCE_LIVE_TRADING",
}

# Matches:
#   os.environ["KEY"]            os.environ['KEY']
#   os.environ.get("KEY", ...)   os.environ.get('KEY')
#   os.getenv("KEY", ...)        os.getenv('KEY')
_ENV_KEY_PATTERN = re.compile(
    r"""os\.(?:environ(?:\.get)?|getenv)\s*[\(\[]\s*['"]([A-Z][A-Z0-9_]+)['"]"""
)


def _collect_env_var_keys() -> set[str]:
    keys: set[str] = set()
    for py in APP_ROOT.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for match in _ENV_KEY_PATTERN.finditer(text):
            keys.add(match.group(1))
    return keys


def test_env_var_key_catalog_exact_match() -> None:
    actual = _collect_env_var_keys()
    missing = EXPECTED_ENV_VAR_KEYS - actual
    extra = actual - EXPECTED_ENV_VAR_KEYS
    assert not missing and not extra, (
        "Environment-variable read-key catalog drift detected under app/. "
        f"Missing: {sorted(missing)}. Extra: {sorted(extra)}. "
        "Any new os.environ/os.getenv read MUST be reviewed because env-var "
        "names are part of the safety surface (operators set them). Update "
        "EXPECTED_ENV_VAR_KEYS only as part of an additive ledger entry that "
        "documents the new variable's safety implication."
    )


def test_safety_kill_vars_remain_present() -> None:
    """The SAFETY_KILL_VARS subset must remain readable from app/.

    These keys gate runtime trading-posture decisions; silently removing a
    read of one (e.g. dropping the APP_ENV gate from app.main) would change
    runtime behaviour."""
    actual = _collect_env_var_keys()
    missing = SAFETY_KILL_VARS - actual
    assert not missing, (
        f"SAFETY_KILL_VARS missing from live env-var reads: {sorted(missing)}. "
        "These variables are part of the runtime safety contract and must "
        "remain consulted by the corresponding service."
    )


def test_no_forbidden_env_var_keys_present() -> None:
    """Drift-lock invariant: no live/auto-trading env keys may be read."""
    actual = _collect_env_var_keys()
    leaked = FORBIDDEN_ENV_VAR_KEYS & actual
    assert not leaked, (
        f"Forbidden live/auto-trading env-var keys are read by app/: "
        f"{sorted(leaked)}. These would silently expose runtime trading "
        "behaviour to the environment. Reading any of these requires an "
        "explicit matrix unlock."
    )


def test_safety_kill_vars_subset_of_full_catalog() -> None:
    """Sanity guard: SAFETY_KILL_VARS ⊆ EXPECTED_ENV_VAR_KEYS."""
    missing = SAFETY_KILL_VARS - EXPECTED_ENV_VAR_KEYS
    assert not missing, (
        "SAFETY_KILL_VARS contains keys not present in EXPECTED_ENV_VAR_KEYS: "
        f"{sorted(missing)}. The safety subset must be a subset of the full "
        "catalog."
    )
