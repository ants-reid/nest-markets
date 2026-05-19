"""Drift-lock pin: Python ``default`` and SQL ``server_default`` values on
safety-critical columns.

Cycle 60 — MH-DRIFTLOCK-DEFAULT-VALUE-CATALOG.

Why this pin exists
-------------------
Cycle 56 already pinned Boolean column defaults across the schema.  This pin
extends that contract to **non-Boolean** safety-critical columns where a
silent default-value change (e.g. ``'pending'`` → ``'approved'`` on
``risk_decisions.approved``, or ``'disarmed'`` → ``'armed'`` on
``trading_control_arming_states.state``) would silently change runtime
trading posture without touching any guard or service code.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

from app.db import models as _models  # noqa: F401  (side-effect: register tables)
from app.db.base import Base


# (table, column) -> ("default_repr", "server_default_repr_or_None")
# default_repr conventions:
#   - scalar literals are repr()'d (str/int/bool)
#   - "uuid4" is the sentinel for the uuid.uuid4 callable default
# server_default_repr is the str() of the server_default.arg, or None if absent.
EXPECTED_SAFETY_DEFAULTS: dict[tuple[str, str], tuple[str, str | None]] = {
    # broker_submit_decisions ------------------------------------------------
    ("broker_submit_decisions", "id"): ("uuid4", None),
    # broker_trade_events ----------------------------------------------------
    ("broker_trade_events", "broker_provider"): ("'ibkr'", None),
    ("broker_trade_events", "source"): ("'broker_account_trades'", None),
    ("broker_trade_events", "id"): ("uuid4", None),
    # execution_modes --------------------------------------------------------
    # NOTE: these "Boolean-like" columns are actually String("inactive")
    # in the ORM.  The Boolean-default catalog (cycle 56) does not cover
    # them; they MUST be pinned here so a silent flip to "active" is caught.
    ("execution_modes", "requires_approval"): ("'inactive'", "inactive"),
    ("execution_modes", "allows_live_orders"): ("'inactive'", "inactive"),
    ("execution_modes", "id"): ("uuid4", None),
    # risk_decisions ---------------------------------------------------------
    # 'pending' is a SAFETY-CRITICAL default: any newly inserted decision
    # MUST default to pending (NOT approved) so an unhandled insert path
    # cannot silently auto-approve a trade.
    ("risk_decisions", "approved"): ("'pending'", None),
    ("risk_decisions", "id"): ("uuid4", None),
    # risk_profiles ----------------------------------------------------------
    ("risk_profiles", "is_active"): ("'inactive'", "inactive"),
    ("risk_profiles", "id"): ("uuid4", None),
    # signals ----------------------------------------------------------------
    ("signals", "id"): ("uuid4", None),
    # trading_control_arming_states -----------------------------------------
    # 'disarmed' is THE safety default for the entire arming-state machine.
    # Flipping it to 'armed' would silently arm trading on every new row.
    ("trading_control_arming_states", "state"): ("'disarmed'", "disarmed"),
    ("trading_control_arming_states", "id"): ("uuid4", None),
}

# Subset of EXPECTED_SAFETY_DEFAULTS that, if changed, is a hard safety
# regression and MUST trigger PR review even if EXPECTED_SAFETY_DEFAULTS is
# updated to match.  Keeping these as a separate, smaller assertion makes
# the safety contract impossible to "accidentally bump" by regenerating the
# bigger catalog.
SAFETY_REQUIRED_DEFAULTS: dict[tuple[str, str], str] = {
    ("execution_modes", "requires_approval"): "'inactive'",
    ("execution_modes", "allows_live_orders"): "'inactive'",
    ("risk_decisions", "approved"): "'pending'",
    ("risk_profiles", "is_active"): "'inactive'",
    ("trading_control_arming_states", "state"): "'disarmed'",
}


def _python_default_repr(col) -> str | None:
    d = col.default
    if d is None:
        return None
    arg = getattr(d, "arg", None)
    if arg is None:
        return None
    if callable(arg):
        # Identify the uuid.uuid4 callable specifically; we don't pin
        # other callables.
        if getattr(arg, "__name__", "") == "uuid4":
            return "uuid4"
        return f"callable:{getattr(arg, '__name__', type(arg).__name__)}"
    return repr(arg)


def _server_default_repr(col) -> str | None:
    sd = col.server_default
    if sd is None:
        return None
    arg = getattr(sd, "arg", None)
    if arg is None:
        return None
    return str(arg)


def _collect_actual_defaults() -> dict[tuple[str, str], tuple[str, str | None]]:
    actual: dict[tuple[str, str], tuple[str, str | None]] = {}
    tables = {tname for (tname, _) in EXPECTED_SAFETY_DEFAULTS.keys()}
    for tname in tables:
        t = Base.metadata.tables[tname]
        for col in t.columns:
            key = (tname, col.name)
            if key not in EXPECTED_SAFETY_DEFAULTS:
                continue
            actual[key] = (
                _python_default_repr(col) or "",
                _server_default_repr(col),
            )
    return actual


def test_safety_default_value_catalog_exact_match() -> None:
    actual = _collect_actual_defaults()
    missing = set(EXPECTED_SAFETY_DEFAULTS.keys()) - set(actual.keys())
    assert not missing, (
        "SAFETY_DEFAULTS catalog drift: expected (table, column) entries are "
        f"missing from the live ORM: {sorted(missing)}. If a column was "
        "intentionally renamed or removed, update EXPECTED_SAFETY_DEFAULTS "
        "AND document the safety implication in docs/build-ledger.md."
    )
    mismatches: list[str] = []
    for key, expected in EXPECTED_SAFETY_DEFAULTS.items():
        got = actual[key]
        if got != expected:
            mismatches.append(f"  {key}: expected={expected!r} got={got!r}")
    assert not mismatches, (
        "Safety-critical default-value drift detected. Any change to a "
        "default for a safety-critical column MUST be reviewed because it "
        "directly changes the trading-posture defaults applied to newly "
        "inserted rows.\n" + "\n".join(mismatches)
    )


def test_safety_required_defaults_remain_inactive() -> None:
    """Stricter pin: the smaller hard-safety subset cannot be loosened.

    These defaults are the runtime safety contract.  Flipping any of them
    silently changes trading posture for every newly inserted row without
    touching any service or guard code.
    """
    actual = _collect_actual_defaults()
    failures: list[str] = []
    for key, expected_python_default in SAFETY_REQUIRED_DEFAULTS.items():
        got_python_default, _ = actual.get(key, ("", None))
        if got_python_default != expected_python_default:
            failures.append(
                f"  {key}: expected python default={expected_python_default!r} "
                f"got={got_python_default!r}"
            )
    assert not failures, (
        "SAFETY_REQUIRED defaults drift detected. These defaults are the "
        "trading-posture safety contract and may not be loosened.\n"
        + "\n".join(failures)
    )


def test_safety_required_defaults_subset_of_full_catalog() -> None:
    """Sanity guard: the smaller hard-safety subset must remain a subset of
    the full catalog so regenerating the full catalog cannot accidentally
    drop a SAFETY_REQUIRED entry."""
    missing = set(SAFETY_REQUIRED_DEFAULTS.keys()) - set(
        EXPECTED_SAFETY_DEFAULTS.keys()
    )
    assert not missing, (
        "SAFETY_REQUIRED_DEFAULTS contains keys not present in "
        f"EXPECTED_SAFETY_DEFAULTS: {sorted(missing)}. This breaks the "
        "two-tier safety contract."
    )
