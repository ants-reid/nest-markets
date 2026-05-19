"""Cycle 57 / Phase B — Index + UniqueConstraint catalog drift-lock.

Schema-catalog meta-pin enumerating every named ``Index`` (``ix_*``) and
``UniqueConstraint`` (``uq_*``) declared across all ORM models. Catches:
  * Silent removal of a uniqueness constraint that prevents duplicate
    rows (e.g. ``uq_pac_provider_asset_tf`` on provider_asset_coverage —
    drift would let the same provider/asset/timeframe row exist twice
    and break coverage aggregations).
  * Silent removal of a query-path index that downstream services
    implicitly depend on for performance (e.g.
    ``ix_signals_status_scan_ts`` is the hot path for the worker
    candidate-selection query).
  * Silent ADDITION of an index/UC, which is also a behaviour change
    worth catching at PR review.

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

# Side-effect import: registers every ORM model on Base.metadata.
from app.db import models as _models  # noqa: F401
from app.db.base import Base
from sqlalchemy import UniqueConstraint


# ---------------------------------------------------------------------------
# UniqueConstraint catalog. (table, name, tuple of column names).
# ---------------------------------------------------------------------------
EXPECTED_UNIQUE_CONSTRAINTS: set[tuple[str, str, tuple[str, ...]]] = {
    ("bars", "uq_bars_asset_timeframe_ts", ("asset_id", "timeframe", "ts")),
    ("broker_trade_events", "uq_broker_trade_event_fingerprint", ("event_fingerprint",)),
    ("feature_snapshots", "uq_feature_snapshots_asset_timeframe_scan_ts",
     ("asset_id", "timeframe", "scan_ts")),
    ("filing_events", "uq_filing_events_asset_type_date",
     ("asset_id", "event_type", "event_date")),
    ("fundamental_snapshots", "uq_fundamental_snapshots_asset_date",
     ("asset_id", "snapshot_date")),
    ("macro_observations", "uq_macro_obs_series_date",
     ("macro_series_id", "observation_date")),
    ("market_regimes", "uq_market_regimes_name_start",
     ("regime_name", "start_date")),
    ("news_items", "uq_news_items_external_source", ("external_id", "source")),
    ("news_symbol_links", "uq_news_symbol_links_item_asset",
     ("news_item_id", "asset_id")),
    ("prompt_versions", "uq_prompt_versions_role_version", ("role", "version")),
    ("provider_asset_coverage", "uq_pac_provider_asset_tf",
     ("provider", "asset_symbol", "timeframe")),
    ("score_model_evaluations", "uq_sme_model_run_metric",
     ("model_registry_id", "evaluation_run_id", "metric_name")),
    ("score_model_parameters", "uq_smp_model_param_regime",
     ("model_registry_id", "parameter_name", "regime_tag")),
    ("score_model_registry", "uq_smr_bucket_asset_version",
     ("strategy_bucket", "asset_class", "version_number")),
    ("trading_control_arming_states", "uq_trading_control_arming_states_scope_mode",
     ("scope", "trading_mode")),
}

# ---------------------------------------------------------------------------
# Named-index catalog. {table_name: sorted list of ix_* index names}.
# ---------------------------------------------------------------------------
EXPECTED_INDEXES: dict[str, list[str]] = {
    "ai_backtest_reports": ["ix_ai_backtest_reports_backtest_run_id", "ix_ai_backtest_reports_status"],
    "assets": ["ix_assets_ibkr_con_id", "ix_assets_symbol"],
    "backtest_runs": ["ix_backtest_runs_status"],
    "bars": ["ix_bars_asset_timeframe_ts"],
    "baseline_candidates": [
        "ix_baseline_candidates_ai_backtest_report_id",
        "ix_baseline_candidates_asset",
        "ix_baseline_candidates_backtest_run_id",
        "ix_baseline_candidates_status",
        "ix_baseline_candidates_strategy_config_id",
        "ix_baseline_candidates_strategy_type",
        "ix_baseline_candidates_timeframe",
    ],
    "broker_trade_events": [
        "ix_broker_trade_events_account_id",
        "ix_broker_trade_events_broker_order_id",
        "ix_broker_trade_events_event_fingerprint",
        "ix_broker_trade_events_symbol",
        "ix_broker_trade_events_trade_ts",
    ],
    "drawdown_periods": ["ix_drawdown_periods_backtest_run_id"],
    "equity_curve_points": [
        "ix_equity_curve_points_backtest_run_id",
        "ix_equity_curve_points_timestamp",
    ],
    "feature_snapshots": ["ix_feature_snapshots_asset_timeframe_scan_ts"],
    "macro_observations": ["ix_macro_obs_date"],
    "market_data_gaps": ["ix_market_data_gaps_asset_symbol"],
    "market_data_import_runs": [
        "ix_market_data_import_runs_asset_symbol",
        "ix_market_data_import_runs_batch_id",
        "ix_market_data_import_runs_provider",
    ],
    "market_data_quality_reports": ["ix_market_data_quality_reports_asset_symbol"],
    "market_regimes": ["ix_market_regimes_start_date"],
    "mock_trades": [
        "ix_mock_trades_asset",
        "ix_mock_trades_backtest_run_id",
        "ix_mock_trades_strategy_config_id",
        "ix_mock_trades_timeframe",
    ],
    "news_articles": ["ix_news_articles_published_at"],
    "news_items": ["ix_news_items_published_at"],
    "opportunity_outcomes": ["ix_opp_outcomes_opportunity_id"],
    "paper_recommendations": [
        "ix_paper_recommendations_model",
        "ix_paper_recommendations_signal",
        "ix_paper_recommendations_status_ts",
    ],
    "paper_validation_events": ["ix_paper_validation_events_paper_validation_plan_id"],
    "paper_validation_evidence": ["ix_paper_validation_evidence_paper_validation_plan_id"],
    "paper_validation_plans": [
        "ix_paper_validation_plans_backtest_run_id",
        "ix_paper_validation_plans_baseline_candidate_id",
        "ix_paper_validation_plans_status",
        "ix_paper_validation_plans_strategy_config_id",
    ],
    "pnl_snapshots": ["ix_pnl_snapshots_snapshot_ts"],
    "provider_asset_coverage": [
        "ix_provider_asset_coverage_asset_symbol",
        "ix_provider_asset_coverage_provider",
    ],
    "provider_coverage_reports": ["ix_provider_coverage_reports_provider"],
    "quality_review_audits": ["ix_quality_review_audits_report_id"],
    "quotes": ["ix_quotes_asset_ts"],
    "research_jobs": ["ix_research_jobs_job_type", "ix_research_jobs_status"],
    "score_model_registry": ["ix_smr_is_active", "ix_smr_status"],
    "scored_opportunities": [
        "ix_scored_opp_asset_scored_at",
        "ix_scored_opp_signal_id",
    ],
    "signal_outcomes": ["ix_signal_outcomes_signal_id"],
    "signals": ["ix_signals_asset_scan_ts", "ix_signals_status_scan_ts"],
    "strategy_configs": ["ix_strategy_configs_asset", "ix_strategy_configs_timeframe"],
    "strategy_results": [
        "ix_strategy_results_asset",
        "ix_strategy_results_backtest_run_id",
        "ix_strategy_results_strategy_config_id",
    ],
    "trading_control_arming_states": [
        "ix_trading_control_arming_states_state_expires_at",
        "ix_trading_control_arming_states_updated_at",
    ],
}

# Hard-pinned safety-critical UniqueConstraints. Drift here is a runtime
# data-integrity regression — duplicate rows would silently appear and
# break aggregations (coverage approval, signal-fingerprint dedup, etc.).
SAFETY_CRITICAL_UNIQUE_CONSTRAINTS: set[tuple[str, str]] = {
    ("bars", "uq_bars_asset_timeframe_ts"),
    ("broker_trade_events", "uq_broker_trade_event_fingerprint"),
    ("provider_asset_coverage", "uq_pac_provider_asset_tf"),
    ("trading_control_arming_states", "uq_trading_control_arming_states_scope_mode"),
}


def _collect_actual_unique_constraints() -> set[tuple[str, str, tuple[str, ...]]]:
    actual: set[tuple[str, str, tuple[str, ...]]] = set()
    for tname, table in Base.metadata.tables.items():
        for c in table.constraints:
            if isinstance(c, UniqueConstraint) and c.name:
                actual.add((tname, c.name, tuple(col.name for col in c.columns)))
    return actual


def _collect_actual_named_indexes() -> dict[str, list[str]]:
    actual: dict[str, list[str]] = {}
    for tname, table in Base.metadata.tables.items():
        named = sorted(
            i.name for i in table.indexes
            if i.name and i.name.startswith("ix_")
        )
        if named:
            actual[tname] = named
    return actual


def test_unique_constraint_catalog_exact_match():
    """No NEW UniqueConstraint may appear without being added to the
    catalog, and no catalog entry may disappear silently."""
    actual = _collect_actual_unique_constraints()
    extra = actual - EXPECTED_UNIQUE_CONSTRAINTS
    missing = EXPECTED_UNIQUE_CONSTRAINTS - actual

    assert not extra, (
        "New UniqueConstraint(s) appeared without catalog entries:\n  "
        + "\n  ".join(sorted(repr(e) for e in extra))
        + "\nAdd each to EXPECTED_UNIQUE_CONSTRAINTS."
    )
    assert not missing, (
        "UniqueConstraint(s) expected by catalog are missing from models:\n  "
        + "\n  ".join(sorted(repr(m) for m in missing))
        + "\nA dedup guard may have been deleted."
    )


def test_safety_critical_unique_constraints_present():
    """Hard pin: the unique constraints in
    ``SAFETY_CRITICAL_UNIQUE_CONSTRAINTS`` must exist. Drift here means
    duplicate rows can silently land (e.g. two provider_asset_coverage
    rows for the same provider/asset/timeframe → wrong approval state)."""
    actual = _collect_actual_unique_constraints()
    actual_keys = {(t, n) for (t, n, _cols) in actual}
    for key in SAFETY_CRITICAL_UNIQUE_CONSTRAINTS:
        assert key in actual_keys, (
            f"SAFETY-CRITICAL UniqueConstraint missing: {key}. "
            "Duplicate rows could now appear silently."
        )


def test_named_index_catalog_exact_match():
    """No named index may appear or disappear without catalog update.
    Performance-regression and silent-removal protection."""
    actual = _collect_actual_named_indexes()

    extra_tables = set(actual.keys()) - set(EXPECTED_INDEXES.keys())
    missing_tables = set(EXPECTED_INDEXES.keys()) - set(actual.keys())

    assert not extra_tables, (
        f"Tables with new named indexes appeared without catalog entries: "
        f"{sorted(extra_tables)}. Add them to EXPECTED_INDEXES."
    )
    assert not missing_tables, (
        f"Tables expected to carry named indexes are missing them: "
        f"{sorted(missing_tables)}. Indexes may have been deleted."
    )

    mismatches: list[str] = []
    for tname, expected_list in EXPECTED_INDEXES.items():
        actual_list = actual[tname]
        if actual_list != expected_list:
            added = set(actual_list) - set(expected_list)
            removed = set(expected_list) - set(actual_list)
            mismatches.append(
                f"  {tname}: added={sorted(added)} removed={sorted(removed)}"
            )
    assert not mismatches, (
        "Named-index drift detected:\n" + "\n".join(mismatches)
        + "\nUpdate EXPECTED_INDEXES. Removing an index that backs a hot "
        "query path is a silent performance regression."
    )


def test_at_least_minimum_indexes_and_uniques_present():
    """Sanity floor: catches catastrophic loss (e.g. import side-effect
    broke and metadata is empty)."""
    ucs = _collect_actual_unique_constraints()
    indexes = _collect_actual_named_indexes()
    assert len(ucs) >= 10, (
        f"Expected at least 10 named UniqueConstraints; found {len(ucs)}."
    )
    total_indexes = sum(len(v) for v in indexes.values())
    assert total_indexes >= 50, (
        f"Expected at least 50 named indexes; found {total_indexes}."
    )
