"""Drift-lock pin: SQL text of safety-critical CHECK constraints.

Cycle 61 — MH-DRIFTLOCK-CHECK-CONSTRAINT-SQL-TEXT.

Why this pin exists
-------------------
``test_check_constraint_catalog_drift_lock.py`` (cycle 56) pins the
**set of names** of CHECK constraints declared in ORM ``__table_args__``.
That catches additions/removals but does NOT catch a silent edit of a
constraint's SQL expression — for example, widening
``state IN ('armed', 'disarmed')`` to
``state IN ('armed', 'disarmed', 'suspended')`` would change runtime
trading-posture validation without altering the constraint name.

This pin freezes the **SQL text** of every safety-critical CHECK so any
expression edit forces an explicit catalog update + ledger entry.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint

from app.db import models as _models  # noqa: F401  (side-effect: register tables)
from app.db.base import Base


# (table_name, constraint_name) -> exact SQL text from CheckConstraint.sqltext.
# These are the trading-posture/safety-state CHECKs whose expression is part
# of the safety contract.  Editing any of these widens or narrows the set
# of accepted values — both directions can be safety failures.
EXPECTED_CHECK_SQL: dict[tuple[str, str], str] = {
    (
        "trading_control_arming_states",
        "ck_trading_control_arming_states_state",
    ): "state IN ('armed', 'disarmed')",
    (
        "trading_control_arming_states",
        "ck_trading_control_arming_states_enablement_status",
    ): "last_enablement_status IS NULL OR last_enablement_status IN ('ready', 'blocked', 'warning')",
    (
        "trading_control_arming_states",
        "ck_trading_control_arming_states_armed_fields",
    ): "state <> 'armed' OR (armed_at IS NOT NULL AND armed_by IS NOT NULL AND expires_at IS NOT NULL)",
    (
        "trading_control_arming_states",
        "ck_trading_control_arming_states_disarmed_expiry",
    ): "state <> 'disarmed' OR expires_at IS NULL",
}

# Subset whose SQL text is a hard-safety contract — widening the allowed-
# values list on these silently expands trading posture.
SAFETY_CRITICAL_CHECKS: set[tuple[str, str]] = {
    (
        "trading_control_arming_states",
        "ck_trading_control_arming_states_state",
    ),
    (
        "trading_control_arming_states",
        "ck_trading_control_arming_states_armed_fields",
    ),
}


def _collect_actual_check_sql() -> dict[tuple[str, str], str]:
    actual: dict[tuple[str, str], str] = {}
    for tname, table in Base.metadata.tables.items():
        for c in table.constraints:
            if isinstance(c, CheckConstraint) and c.name:
                actual[(tname, c.name)] = str(c.sqltext)
    return actual


def test_safety_check_constraint_sql_text_unchanged() -> None:
    actual = _collect_actual_check_sql()
    failures: list[str] = []
    for key, expected_sql in EXPECTED_CHECK_SQL.items():
        if key not in actual:
            failures.append(
                f"  {key}: MISSING from live ORM (constraint deleted or "
                "renamed)"
            )
            continue
        if actual[key] != expected_sql:
            failures.append(
                f"  {key}:\n    expected: {expected_sql!r}\n    actual:   {actual[key]!r}"
            )
    assert not failures, (
        "Safety-critical CHECK-constraint SQL text drift detected. Editing "
        "any of these expressions changes runtime validation of trading "
        "posture rows. Update EXPECTED_CHECK_SQL only as part of an "
        "explicit ledger entry that documents the safety implication.\n"
        + "\n".join(failures)
    )


def test_safety_critical_checks_remain_present() -> None:
    """The safety-critical subset must remain present (no silent deletion)."""
    actual = _collect_actual_check_sql()
    missing = SAFETY_CRITICAL_CHECKS - set(actual.keys())
    assert not missing, (
        f"Safety-critical CHECK constraints missing from live ORM: "
        f"{sorted(missing)}. Deleting these would remove DB-level "
        "enforcement of trading-posture allowed values."
    )


def test_arming_state_allowed_values_unchanged() -> None:
    """Specifically pin the arming-state allowed values to ('armed','disarmed').

    Widening this set (e.g. adding 'suspended', 'warming-up') would silently
    change the posture-state machine's accepted vocabulary without touching
    any service code.
    """
    actual = _collect_actual_check_sql()
    sql = actual[
        (
            "trading_control_arming_states",
            "ck_trading_control_arming_states_state",
        )
    ]
    assert "'armed'" in sql and "'disarmed'" in sql, (
        f"Arming-state CHECK no longer references both 'armed' and "
        f"'disarmed': {sql!r}"
    )
    # Defensive: the only allowed values must be those two.  Reject any
    # other quoted string literal in the expression.
    import re

    quoted = set(re.findall(r"'([^']+)'", sql))
    assert quoted == {"armed", "disarmed"}, (
        f"Arming-state CHECK now allows additional states: {quoted}. "
        "Widening the allowed-values set requires explicit safety review."
    )
