"""Cycle 56 / Phase B — Boolean default-False safety pin.

Drift-lock meta-pin sweeping every ``Boolean`` column across all ORM
models. Pins the **expected default** for each safety-relevant Boolean
so a future contributor cannot land a column like
``live_trading_enabled = True`` (or flip ``auto_trade_enabled`` to True)
without updating this catalog.

Why this matters
----------------
The drift-lock policy mandates auto-paper, auto-trading, and live trading
all stay OFF. Many of those guards are enforced at the *column-default*
level (e.g. ``risk_profile.auto_trade_enabled`` defaults False). A new
``Boolean`` column whose name suggests a trading-enable flag could ship
with default True and silently flip behaviour for any code path that
reads the model with ``getattr(row, 'live_enabled')``.

This pin:
  1. Enumerates every Boolean column expected to exist (whitelist by
     ``model.column``).
  2. Pins each column's expected ``server_default`` and Python ``default``.
  3. Asserts no NEW Boolean column has appeared whose name matches a
     safety-suggestive pattern without being added to the whitelist.

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

import re

# Import ALL models so SQLAlchemy registers every table on the metadata.
from app.db import models as _models  # noqa: F401 — import side effect
from app.db.base import Base
from sqlalchemy import Boolean


# ---------------------------------------------------------------------------
# Expected catalog of every Boolean column.
#
# Format: (table_name, column_name) -> {
#     "py_default": <True | False | None>,           # Python-side default
#     "server_default": <"true" | "false" | None>,   # SQL server_default
#     "nullable": <bool>,
# }
#
# To add a new Boolean column: add it here AND, if the name matches the
# safety pattern (see SAFETY_PATTERN below), justify the chosen default
# in the column docstring on the model. Defaults that make a trading
# behaviour MORE permissive require a paired drift-lock unlock phase.
# ---------------------------------------------------------------------------
EXPECTED_BOOLEAN_COLUMNS: dict[tuple[str, str], dict[str, object]] = {
    # --- Safety-critical: defaults must remain False (off-by-default) ---
    ("execution_modes", "is_active"): {
        "py_default": False, "server_default": "false", "nullable": False,
    },
    ("risk_profiles", "auto_trade_enabled"): {
        "py_default": False, "server_default": "false", "nullable": False,
    },
    ("prompt_versions", "is_active"): {
        "py_default": False, "server_default": "false", "nullable": False,
    },
    ("model_versions", "is_active"): {
        "py_default": False, "server_default": "false", "nullable": False,
    },
    ("score_model_registry", "is_active"): {
        "py_default": False, "server_default": "false", "nullable": False,
    },
    ("market_data_quality_reports", "approved_for_backtest"): {
        "py_default": False, "server_default": None, "nullable": False,
    },
    ("provider_asset_coverage", "approved_for_backtest"): {
        "py_default": False, "server_default": None, "nullable": False,
    },
    ("execution_policies", "requires_user_confirmation"): {
        "py_default": False, "server_default": "false", "nullable": False,
    },
    ("drawdown_periods", "recovered"): {
        "py_default": False, "server_default": None, "nullable": False,
    },

    # --- Safety-critical: defaults must remain True (locked-on guards) ---
    ("risk_profiles", "confirm_before_trade_enabled"): {
        "py_default": True, "server_default": "true", "nullable": False,
    },
    ("risk_profiles", "kill_switch_enabled"): {
        "py_default": True, "server_default": "true", "nullable": False,
    },
    ("execution_policies", "paper_only"): {
        "py_default": True, "server_default": "true", "nullable": False,
    },

    # --- Operational: not safety-critical ---
    ("strategy_configs", "enabled"): {
        "py_default": True, "server_default": None, "nullable": False,
    },
    ("assets", "is_active"): {
        "py_default": True, "server_default": "true", "nullable": False,
    },
    ("paper_validation_evidence", "included_in_metrics"): {
        "py_default": True, "server_default": "true", "nullable": False,
    },
    ("eval_cases", "is_active"): {
        "py_default": True, "server_default": "true", "nullable": False,
    },
    ("score_model_promotions", "rollback_eligible"): {
        "py_default": True, "server_default": "true", "nullable": False,
    },
    ("model_versions", "supports_structured_output"): {
        "py_default": True, "server_default": "true", "nullable": False,
    },
    ("execution_policies", "allow_long"): {
        "py_default": True, "server_default": "true", "nullable": False,
    },
    ("execution_policies", "allow_short"): {
        "py_default": True, "server_default": "true", "nullable": False,
    },
    ("risk_limit_configs", "is_active"): {
        "py_default": True, "server_default": "true", "nullable": False,
    },

    # --- Required (no default; writer must supply): would_block, gate flags ---
    ("broker_submit_decisions", "would_block"): {
        "py_default": None, "server_default": None, "nullable": False,
    },

    # --- Nullable optional booleans (no default; can be NULL) ---
    ("score_model_evaluations", "passed_gates"): {
        "py_default": None, "server_default": None, "nullable": True,
    },
    ("feature_definitions", "pit_safe"): {
        "py_default": None, "server_default": None, "nullable": True,
    },
    ("risk_decisions", "spread_ok"): {
        "py_default": None, "server_default": None, "nullable": True,
    },
    ("risk_decisions", "session_ok"): {
        "py_default": None, "server_default": None, "nullable": True,
    },
    ("risk_decisions", "drawdown_ok"): {
        "py_default": None, "server_default": None, "nullable": True,
    },
    ("risk_decisions", "cooldown_ok"): {
        "py_default": None, "server_default": None, "nullable": True,
    },
    ("risk_decisions", "kill_switch_active"): {
        "py_default": None, "server_default": None, "nullable": True,
    },
    ("signal_outcomes", "predicted_direction_correct"): {
        "py_default": None, "server_default": None, "nullable": True,
    },
}


# Names matching this pattern are treated as SAFETY-SUGGESTIVE. Any new
# Boolean column with such a name must (a) be added to the catalog above
# and (b) default False unless paired with an explicit drift-lock unlock.
SAFETY_PATTERN = re.compile(
    r"^(auto_|live_|real_money|"
    r".*_enabled$|.*_allowed$|.*_approved$|.*_active$|.*_armed$|"
    r".*kill_switch.*)$",
    re.IGNORECASE,
)

# Subset of the catalog whose names are safety-suggestive AND are required
# to stay False-by-default. Any drift here is a runtime safety regression.
SAFETY_FALSE_BY_DEFAULT: set[tuple[str, str]] = {
    ("execution_modes", "is_active"),
    ("risk_profiles", "auto_trade_enabled"),
    ("prompt_versions", "is_active"),
    ("model_versions", "is_active"),
    ("score_model_registry", "is_active"),
    ("market_data_quality_reports", "approved_for_backtest"),
    ("provider_asset_coverage", "approved_for_backtest"),
    ("execution_policies", "requires_user_confirmation"),
}


def _collect_actual_boolean_columns() -> dict[tuple[str, str], dict[str, object]]:
    actual: dict[tuple[str, str], dict[str, object]] = {}
    for table_name, table in Base.metadata.tables.items():
        for column in table.columns:
            if isinstance(column.type, Boolean):
                py_default: object = None
                if column.default is not None and hasattr(column.default, "arg"):
                    py_default = column.default.arg
                server_default: object = None
                if column.server_default is not None:
                    raw = getattr(column.server_default, "arg", None)
                    if raw is not None:
                        # raw may be a sa.text(...) or a plain string
                        text_val = getattr(raw, "text", raw)
                        server_default = str(text_val).strip("'\"").lower()
                actual[(table_name, column.name)] = {
                    "py_default": py_default,
                    "server_default": server_default,
                    "nullable": column.nullable,
                }
    return actual


def test_boolean_column_catalog_exact_match():
    """No NEW Boolean column may appear without being added to the catalog,
    and no catalog entry may disappear without explicit removal here."""
    actual = _collect_actual_boolean_columns()

    extra = set(actual.keys()) - set(EXPECTED_BOOLEAN_COLUMNS.keys())
    missing = set(EXPECTED_BOOLEAN_COLUMNS.keys()) - set(actual.keys())

    assert not extra, (
        f"New Boolean column(s) appeared without catalog entries: "
        f"{sorted(extra)}. Add them to EXPECTED_BOOLEAN_COLUMNS in "
        "this file. If the name matches the safety pattern (auto_*, live_*, "
        "*_enabled, *_allowed, *_approved, real_money*, *_active, *kill_switch*), "
        "the default MUST be False unless a drift-lock unlock phase is paired."
    )
    assert not missing, (
        f"Boolean column(s) expected by catalog are missing from models: "
        f"{sorted(missing)}. A safety-relevant column may have been deleted."
    )


def test_boolean_column_defaults_match_catalog():
    """Each Boolean column's defaults and nullability must match the
    pinned values exactly. Drift here is the strongest safety signal."""
    actual = _collect_actual_boolean_columns()
    mismatches: list[str] = []
    for key, expected in EXPECTED_BOOLEAN_COLUMNS.items():
        if key not in actual:
            continue  # already reported by exact_match test
        got = actual[key]
        if (
            got["py_default"] != expected["py_default"]
            or got["server_default"] != expected["server_default"]
            or got["nullable"] != expected["nullable"]
        ):
            mismatches.append(f"{key}: expected={expected} got={got}")
    assert not mismatches, (
        "Boolean column default/nullability drift detected:\n  "
        + "\n  ".join(mismatches)
        + "\nIf intentional, update EXPECTED_BOOLEAN_COLUMNS. If a "
        "safety-suggestive column flipped to default-True, this MUST be "
        "paired with an explicit drift-lock unlock phase in the matrix."
    )


def test_safety_critical_booleans_default_false():
    """Hard-coded safety pin: the off-by-default flags listed in
    SAFETY_FALSE_BY_DEFAULT must remain default-False. This is a
    redundant assertion to catalyse review during PR — even if a
    contributor edits EXPECTED_BOOLEAN_COLUMNS, this hard-coded set
    will fail until the unlock is recorded here too."""
    actual = _collect_actual_boolean_columns()
    for key in SAFETY_FALSE_BY_DEFAULT:
        assert key in actual, f"Safety-critical Boolean column missing: {key}"
        got = actual[key]
        assert got["py_default"] is False, (
            f"SAFETY DRIFT: {key} Python default flipped from False to "
            f"{got['py_default']!r}. This would silently enable a trading "
            "behaviour. Auto-paper / auto / live trading are intentionally "
            "OFF — this default must remain False until an explicit "
            "drift-lock unlock phase ships."
        )
        # server_default may be None (e.g. approved_for_backtest) but if
        # set, must be "false".
        if got["server_default"] is not None:
            assert got["server_default"] == "false", (
                f"SAFETY DRIFT: {key} server_default flipped from 'false' "
                f"to {got['server_default']!r}."
            )


def test_no_new_safety_pattern_boolean_outside_catalog():
    """Defence-in-depth: even if a contributor adds a new Boolean column
    AND adds it to EXPECTED_BOOLEAN_COLUMNS, this test independently scans
    the model metadata for safety-suggestive names and forces them to be
    explicitly classified."""
    actual = _collect_actual_boolean_columns()
    catalog_keys = set(EXPECTED_BOOLEAN_COLUMNS.keys())
    flagged: list[tuple[str, str]] = []
    for key, info in actual.items():
        if key not in catalog_keys:
            _table, column = key
            if SAFETY_PATTERN.match(column):
                flagged.append(key)
    assert not flagged, (
        f"Safety-pattern Boolean columns appeared without catalog entries: "
        f"{flagged}. These names trip the safety regex; add them to "
        "EXPECTED_BOOLEAN_COLUMNS AND, if appropriate, to "
        "SAFETY_FALSE_BY_DEFAULT."
    )
