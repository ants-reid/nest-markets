"""Cycle 56 / Phase A — Model-level ``CheckConstraint`` catalog pin.

Drift-lock meta-pin complementing the per-table schema pins shipped in
cycles 50–55. This file pins the **complete inventory of ORM-declared
``CheckConstraint`` objects** across ``apps/api/app/db/models/``.

Why this matters
----------------
Per-table drift-lock tests assert that *expected* constraints exist, but
none of them catch the symmetric failure mode: a future contributor
silently *adds* a ``CheckConstraint`` to a model and ships it without
review. A new CHECK on a safety-critical table (e.g. ``risk_profiles``,
``broker_submit_decisions``, ``signals``) is a runtime-behaviour change —
the catalog pin forces every addition or deletion through this file.

Drift-lock confirmation
-----------------------
* Pure additive test file. No production code touched.
* No migration. No DB write. No worker change.
* ``assert_auto_trading_allowed()`` UNCHANGED — still raises unconditionally.
* ``BrokerService.submit_auto_order`` UNCHANGED.
* Auto-paper enforcement remains OFF. Auto trading remains OFF.
  Live trading remains OFF.
"""

from __future__ import annotations

# Import ALL models so SQLAlchemy registers every table on the metadata.
# This is the same pattern other catalog-style drift-lock tests use
# (e.g. test_alembic_head_drift_lock.py, test_enum_membership_drift_lock.py).
from app.db import models as _models  # noqa: F401 — import side effect
from app.db.base import Base
from sqlalchemy import CheckConstraint


# ---------------------------------------------------------------------------
# Expected catalog — every (table_name, constraint_name) pair declared in an
# ORM model's ``__table_args__``. To add or remove a model-level CheckConstraint,
# update this dict in the same PR — and add a per-table drift-lock test that
# pins the SQL expression of the new constraint.
#
# NOTE: Migration-only CHECK constraints (e.g.
# ``ck_news_articles_evidence_class_research_only``) are NOT included here —
# they are pinned via live-DB pg_catalog queries in their per-table tests
# (see ``test_news_article_schema_drift_lock.py`` and
# ``test_news_in_decision_log_schema_drift_lock.py``).
# ---------------------------------------------------------------------------
EXPECTED_MODEL_CHECK_CONSTRAINTS: dict[str, set[str]] = {
    "trading_control_arming_states": {
        "ck_trading_control_arming_states_state",
        "ck_trading_control_arming_states_enablement_status",
        "ck_trading_control_arming_states_armed_fields",
        "ck_trading_control_arming_states_disarmed_expiry",
    },
}


def _collect_actual_model_check_constraints() -> dict[str, set[str]]:
    """Walk Base.metadata.tables and harvest every named CheckConstraint."""
    actual: dict[str, set[str]] = {}
    for table_name, table in Base.metadata.tables.items():
        named: set[str] = set()
        for constraint in table.constraints:
            if isinstance(constraint, CheckConstraint) and constraint.name:
                # Skip auto-generated names from Boolean columns etc. by
                # only counting constraints with explicit ck_ prefix.
                if constraint.name.startswith("ck_"):
                    named.add(constraint.name)
        if named:
            actual[table_name] = named
    return actual


def test_model_check_constraint_catalog_exact_match():
    """Every model-declared CheckConstraint must be in the expected catalog,
    and every catalog entry must exist in the live model metadata.

    Failure modes this catches:
      * Silent ADDITION: contributor adds a new ``CheckConstraint(...)`` to
        a model's ``__table_args__`` without updating this catalog. Forces
        review.
      * Silent REMOVAL: contributor deletes one of the expected constraints
        (e.g. removes ``ck_trading_control_arming_states_armed_fields``,
        which would let an "armed" arming state row exist without an
        ``armed_at`` timestamp — a safety-attribution leak).
    """
    actual = _collect_actual_model_check_constraints()

    extra_tables = set(actual.keys()) - set(EXPECTED_MODEL_CHECK_CONSTRAINTS.keys())
    missing_tables = set(EXPECTED_MODEL_CHECK_CONSTRAINTS.keys()) - set(actual.keys())

    assert not extra_tables, (
        f"New ORM-declared CheckConstraint(s) appeared on tables not in "
        f"the catalog: {sorted(extra_tables)}. "
        "Update EXPECTED_MODEL_CHECK_CONSTRAINTS in this file AND add a "
        "per-table drift-lock test pinning the SQL expression of each new "
        "constraint."
    )
    assert not missing_tables, (
        f"Tables expected to carry model-level CheckConstraint(s) are "
        f"missing them: {sorted(missing_tables)}. A safety constraint "
        "may have been deleted."
    )

    for table_name, expected_names in EXPECTED_MODEL_CHECK_CONSTRAINTS.items():
        actual_names = actual[table_name]
        added = actual_names - expected_names
        removed = expected_names - actual_names
        assert not added, (
            f"Table {table_name!r} has new model-level CheckConstraint(s) "
            f"not in catalog: {sorted(added)}. Add them to "
            "EXPECTED_MODEL_CHECK_CONSTRAINTS."
        )
        assert not removed, (
            f"Table {table_name!r} is missing expected CheckConstraint(s): "
            f"{sorted(removed)}. A safety guard may have been deleted."
        )


def test_trading_control_arming_state_check_constraints_use_ck_prefix():
    """Every named CheckConstraint must use the ``ck_`` prefix so the
    catalog walk above is reliable. Drift here would cause new constraints
    to slip past ``test_model_check_constraint_catalog_exact_match``."""
    table = Base.metadata.tables["trading_control_arming_states"]
    for constraint in table.constraints:
        if isinstance(constraint, CheckConstraint) and constraint.name:
            assert constraint.name.startswith("ck_"), (
                f"CheckConstraint name {constraint.name!r} on "
                "trading_control_arming_states does not use the 'ck_' "
                "prefix; catalog walk would silently miss it."
            )


def test_at_least_one_model_check_constraint_exists():
    """Sanity: if this drops to zero, the import-side-effect of loading
    ``app.db.models`` may have broken (which would silently weaken every
    other catalog-walk pin in the suite)."""
    actual = _collect_actual_model_check_constraints()
    total = sum(len(v) for v in actual.values())
    assert total >= 4, (
        f"Expected at least 4 model-level CheckConstraints (the four on "
        f"trading_control_arming_states); found {total}. Either constraints "
        "were deleted OR `app.db.models` import side-effect broke."
    )
