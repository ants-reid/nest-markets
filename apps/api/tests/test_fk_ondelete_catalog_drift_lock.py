"""Cycle 57 / Phase A — Foreign-key ``ondelete`` catalog drift-lock.

Schema-catalog meta-pin enumerating every ``ForeignKey`` declared across
``apps/api/app/db/models/`` with its ``ondelete`` clause. Catches silent
CASCADE additions to safety-critical tables and silent removal of
existing CASCADE/RESTRICT/SET NULL semantics.

Why this matters
----------------
A future contributor adding ``ondelete="CASCADE"`` to a foreign key on a
trading or audit table is a runtime-behaviour change. Example anti-pattern:
``signals.asset_id ondelete="CASCADE"`` would silently delete every signal
when an asset row is removed, destroying the audit trail. The opposite is
also dangerous: removing CASCADE from ``news_symbol_links.news_item_id``
would orphan rows. Both directions go through this catalog.

The catalog also encodes the SAFETY-CRITICAL invariant that no FK from
trading-decision tables (``signals``, ``risk_decisions``, ``positions``,
``paper_orders``, ``paper_fills``, ``signal_outcomes``,
``broker_submit_decisions``) uses ``ondelete="CASCADE"`` against the
``assets`` parent — these must remain ``ondelete=None`` (NO ACTION) so
asset deactivation cannot delete history.

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


# (source_table, source_column, target_table, target_column, ondelete)
EXPECTED_FOREIGN_KEYS: set[tuple[str, str, str, str, str | None]] = {
    # Approval / eval (no cascade — keep history)
    ("approval_requests", "signal_id", "signals", "id", None),
    ("eval_runs", "model_version_id", "model_versions", "id", None),
    ("eval_runs", "prompt_version_id", "prompt_versions", "id", None),

    # Market data (no cascade on bars/quotes — price history must survive
    # asset deactivation)
    ("bars", "asset_id", "assets", "id", None),
    ("quotes", "asset_id", "assets", "id", None),

    # Feature snapshots / signals graph (no cascade — pinned for audit)
    ("feature_snapshots", "asset_id", "assets", "id", None),
    ("feature_snapshots", "signal_id", "signals", "id", None),
    ("signals", "asset_id", "assets", "id", None),
    ("signals", "feature_snapshot_id", "feature_snapshots", "id", None),
    ("signals", "model_version_id", "model_versions", "id", None),
    ("signals", "prompt_version_id", "prompt_versions", "id", None),

    # Filings / fundamentals / news (CASCADE allowed — pure derivative data
    # tied to a parent the operator chose to delete)
    ("filing_events", "asset_id", "assets", "id", "CASCADE"),
    ("fundamental_snapshots", "asset_id", "assets", "id", "CASCADE"),
    ("macro_observations", "macro_series_id", "macro_series", "id", "CASCADE"),
    ("news_symbol_links", "asset_id", "assets", "id", "CASCADE"),
    ("news_symbol_links", "news_item_id", "news_items", "id", "CASCADE"),

    # Opportunity ranking graph (CASCADE allowed — derived from signals)
    ("missed_opportunity_labels", "opportunity_id", "scored_opportunities", "id", "CASCADE"),
    ("missed_opportunity_labels", "signal_id", "signals", "id", "CASCADE"),
    ("opportunity_outcomes", "opportunity_id", "scored_opportunities", "id", "CASCADE"),
    ("opportunity_outcomes", "signal_id", "signals", "id", "CASCADE"),
    ("scored_opportunities", "asset_id", "assets", "id", "CASCADE"),
    ("scored_opportunities", "signal_id", "signals", "id", "CASCADE"),
    ("scored_opportunities", "model_version_id", "score_model_registry", "id", "SET NULL"),

    # Paper execution graph (NO CASCADE — durable trade history)
    ("paper_fills", "paper_order_id", "paper_orders", "id", None),
    ("paper_orders", "signal_id", "signals", "id", None),
    ("paper_recommendations", "model_version_id", "model_versions", "id", None),
    ("paper_recommendations", "signal_id", "signals", "id", None),
    ("paper_validation_events", "paper_validation_plan_id", "paper_validation_plans", "id", None),
    ("paper_validation_evidence", "paper_validation_plan_id", "paper_validation_plans", "id", None),
    ("positions", "asset_id", "assets", "id", None),
    ("positions", "signal_id", "signals", "id", None),

    # Quality review (CASCADE OK — audit child of a deleted quality report)
    ("quality_review_audits", "report_id", "market_data_quality_reports", "id", "CASCADE"),

    # Risk decisions (NO CASCADE — durable safety audit)
    ("risk_decisions", "signal_id", "signals", "id", None),

    # Score model lifecycle (RESTRICT — block delete to force explicit
    # rollback; SET NULL on optional from_model — promotion can survive
    # parent removal in audit form)
    ("score_model_evaluations", "model_registry_id", "score_model_registry", "id", "RESTRICT"),
    ("score_model_parameters", "model_registry_id", "score_model_registry", "id", "RESTRICT"),
    ("score_model_promotions", "from_model_id", "score_model_registry", "id", "SET NULL"),
    ("score_model_promotions", "to_model_id", "score_model_registry", "id", "RESTRICT"),
    ("score_model_rollbacks", "from_model_id", "score_model_registry", "id", "RESTRICT"),
    ("score_model_rollbacks", "to_model_id", "score_model_registry", "id", "RESTRICT"),

    # Signal outcomes (NO CASCADE — outcome must outlive the signal record
    # for learning-loop reconstruction)
    ("signal_outcomes", "asset_id", "assets", "id", None),
    ("signal_outcomes", "signal_id", "signals", "id", None),
}


# Trading + audit tables whose FKs MUST remain non-CASCADE against the
# assets parent. Tested separately as a hard safety guard.
SAFETY_NO_CASCADE_TO_ASSETS: set[tuple[str, str]] = {
    ("bars", "asset_id"),
    ("quotes", "asset_id"),
    ("feature_snapshots", "asset_id"),
    ("signals", "asset_id"),
    ("positions", "asset_id"),
    ("signal_outcomes", "asset_id"),
}


def _collect_actual_foreign_keys() -> set[tuple[str, str, str, str, str | None]]:
    actual: set[tuple[str, str, str, str, str | None]] = set()
    for tname, table in Base.metadata.tables.items():
        for fk in table.foreign_keys:
            actual.add(
                (
                    tname,
                    fk.parent.name,
                    fk.column.table.name,
                    fk.column.name,
                    fk.ondelete,
                )
            )
    return actual


def test_foreign_key_catalog_exact_match():
    """No NEW FK may appear without being added to the catalog, and no
    catalog entry may disappear silently. Drift in either direction is
    a behaviour change."""
    actual = _collect_actual_foreign_keys()
    extra = actual - EXPECTED_FOREIGN_KEYS
    missing = EXPECTED_FOREIGN_KEYS - actual

    assert not extra, (
        "New ForeignKey(s) appeared without catalog entries:\n  "
        + "\n  ".join(sorted(repr(e) for e in extra))
        + "\nAdd each to EXPECTED_FOREIGN_KEYS in this file. If the FK is "
        "from a safety-critical table to ``assets``, also add it to "
        "SAFETY_NO_CASCADE_TO_ASSETS."
    )
    assert not missing, (
        "ForeignKey(s) expected by catalog are missing from models:\n  "
        + "\n  ".join(sorted(repr(m) for m in missing))
        + "\nA durable referential constraint may have been deleted."
    )


def test_safety_critical_tables_do_not_cascade_to_assets():
    """Hard safety guard. The trading + audit tables in
    ``SAFETY_NO_CASCADE_TO_ASSETS`` must NEVER cascade-delete on
    ``assets``. Asset deactivation must not silently destroy price
    history, signals, positions, or outcomes."""
    actual = _collect_actual_foreign_keys()
    by_source: dict[tuple[str, str], tuple[str, str, str | None]] = {
        (src_t, src_c): (tgt_t, tgt_c, ondelete)
        for src_t, src_c, tgt_t, tgt_c, ondelete in actual
    }
    for key in SAFETY_NO_CASCADE_TO_ASSETS:
        assert key in by_source, (
            f"SAFETY-CRITICAL FK missing entirely: {key} → assets.id. "
            "A durable referential link to assets was deleted."
        )
        tgt_t, tgt_c, ondelete = by_source[key]
        assert tgt_t == "assets" and tgt_c == "id", (
            f"SAFETY-CRITICAL FK {key} should target assets.id, "
            f"got {tgt_t}.{tgt_c}."
        )
        assert ondelete is None, (
            f"SAFETY DRIFT: FK {key} → assets.id has ondelete={ondelete!r}; "
            "must remain None (NO ACTION) so asset deactivation cannot "
            "silently destroy trading/audit history."
        )


def test_at_least_one_foreign_key_present():
    """Sanity floor: if this drops to zero, ``app.db.models`` import
    side-effect broke and every catalog-walk pin is silently a no-op."""
    actual = _collect_actual_foreign_keys()
    assert len(actual) >= 30, (
        f"Expected at least 30 foreign keys; found {len(actual)}. "
        "Either FKs were deleted OR ``app.db.models`` import broke."
    )
