"""Drift-lock: pin the FastAPI route registry.

Cycle 58 — MH-DRIFTLOCK-ROUTE-REGISTRY (pure additive test-only).

Purpose
-------
Enumerate every ``(method, path)`` pair registered on the FastAPI ``app``
and pin the catalog. If anyone adds, removes, or renames an HTTP route,
this test will fail in code review and force an explicit deliberation —
especially valuable for any new mutating endpoints under ``/broker``,
``/orders``, ``/trading``, ``/execution`` (live), or anything that could
plausibly cross the auto-trading boundary.

This file does not import or invoke ``trading_control_service`` or the
broker; it only introspects ``app.routes``. It is read-only and does not
touch the DB.

Drift-lock guarantees
---------------------
* Auto-paper enforcement remains OFF.
* Auto trading remains OFF.
* Live trading remains OFF.
* ``assert_auto_trading_allowed()`` is unchanged.
"""

from __future__ import annotations

from app.main import app


def _collect_method_path_pairs() -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for route in app.routes:
        methods = getattr(route, "methods", None)
        if not methods:
            continue
        for method in methods:
            if method in ("HEAD", "OPTIONS"):
                continue
            pairs.add((method, route.path))
    return pairs


# Hard-coded catalog snapshot taken at cycle 58 from the running FastAPI app.
# Adding or removing a row here requires a paired ledger entry. Renames must
# be split into a remove+add pair so each side is reviewed.
EXPECTED_ROUTES: set[tuple[str, str]] = {
    # --- DELETE ---
    ("DELETE", "/assets/{asset_id}"),
    ("DELETE", "/broker/orders/{broker_order_id}"),
    ("DELETE", "/models/{model_version_id}"),
    # --- GET ---
    ("GET", "/approvals/alerts/active"),
    ("GET", "/approvals/alerts/notifications"),
    ("GET", "/approvals/alerts/rules"),
    ("GET", "/asset-cards/snapshot"),
    ("GET", "/asset-cards/{asset_id}"),
    ("GET", "/assets"),
    ("GET", "/baseline-candidates"),
    ("GET", "/baseline-candidates/{candidate_id}"),
    ("GET", "/broker/account"),
    ("GET", "/broker/control"),
    ("GET", "/broker/daily-pnl"),
    ("GET", "/broker/health"),
    ("GET", "/broker/mode"),
    ("GET", "/broker/orders/audit"),
    ("GET", "/broker/orders/{broker_order_id}/status"),
    ("GET", "/broker/positions"),
    ("GET", "/broker/submit-decisions/recent"),
    ("GET", "/broker/trades/normalized"),
    ("GET", "/cockpit/auto-paper/status"),
    ("GET", "/cockpit/eod-report"),
    ("GET", "/cockpit/in-flight-adjustments"),
    ("GET", "/cockpit/trade-close-explanations"),
    ("GET", "/cockpit/mode"),
    ("GET", "/cockpit/notifications/digest"),
    ("GET", "/docs"),
    ("GET", "/docs/oauth2-redirect"),
    ("GET", "/evals/runs"),
    ("GET", "/evals/runs/{run_id}"),
    ("GET", "/execution/paper"),
    ("GET", "/execution/paper/{execution_id}"),
    ("GET", "/execution/paper/{execution_id}/history"),
    ("GET", "/execution/paper/{execution_id}/journal"),
    ("GET", "/execution/positions"),
    ("GET", "/execution/positions/{position_id}/pnl"),
    ("GET", "/health"),
    ("GET", "/health/providers"),
    ("GET", "/health/safety"),
    ("GET", "/health/services"),
    ("GET", "/llm-logs/recent"),
    ("GET", "/market-data/auto-paper/arming"),
    ("GET", "/market-data/auto-paper/enablement-preconditions"),
    ("GET", "/market-data/auto-paper/history"),
    ("GET", "/market-data/auto-paper/history/export"),
    ("GET", "/market-data/auto-paper/history/retention"),
    ("GET", "/market-data/auto-paper/history/summary"),
    ("GET", "/market-data/auto-paper/kill-switch"),
    ("GET", "/market-data/auto-paper/readiness"),
    ("GET", "/market-data/auto-paper/scheduler/status"),
    ("GET", "/market-data/bars/{asset_symbol}"),
    ("GET", "/market-data/news/{ticker}"),
    ("GET", "/market-data/status"),
    ("GET", "/markets/snapshot"),
    ("GET", "/models"),
    ("GET", "/models/active"),
    ("GET", "/models/{model_version_id}"),
    ("GET", "/monitor/feeds"),
    ("GET", "/monitor/health-history"),
    ("GET", "/monitor/incidents"),
    ("GET", "/monitor/worker-run-log/overview"),
    ("GET", "/news-articles/recent"),
    ("GET", "/news-in-decision-log/recent"),
    ("GET", "/openapi.json"),
    ("GET", "/opportunities"),
    ("GET", "/options/contracts/{conid}"),
    ("GET", "/options/expirations/{conid}"),
    ("GET", "/options/strikes/{conid}"),
    ("GET", "/paper-validation/dashboard"),
    ("GET", "/paper-validation/plans"),
    ("GET", "/paper-validation/plans/{plan_id}"),
    ("GET", "/paper-validation/plans/{plan_id}/events"),
    ("GET", "/paper-validation/plans/{plan_id}/evidence"),
    ("GET", "/paper-validation/plans/{plan_id}/progress"),
    ("GET", "/paper-validation/plans/{plan_id}/readiness"),
    ("GET", "/paper/recommendations"),
    ("GET", "/paper/recommendations/{recommendation_id}"),
    ("GET", "/performance-stats"),
    ("GET", "/prompts"),
    ("GET", "/prompts/{subdir}/{filename}"),
    ("GET", "/prompts/{subdir}/{filename}/history"),
    ("GET", "/redoc"),
    ("GET", "/regime/current"),
    ("GET", "/regime/history"),
    ("GET", "/research/data/assets"),
    ("GET", "/research/data/coverage"),
    ("GET", "/research/data/gaps"),
    ("GET", "/research/data/import-runs"),
    ("GET", "/research/data/providers"),
    ("GET", "/research/data/quality"),
    ("GET", "/research/data/quality/outliers"),
    ("GET", "/research/data/quality/outliers/summary"),
    ("GET", "/research/data/quality/outliers/{report_id}/audit"),
    ("GET", "/research/jobs"),
    ("GET", "/research/jobs/{job_id}"),
    ("GET", "/risk-decisions/recent"),
    ("GET", "/risk/limits"),
    ("GET", "/risk/limits/status"),
    ("GET", "/scoring/active"),
    ("GET", "/scoring/explain/{signal_id}"),
    ("GET", "/signals/{signal_id}/features"),
    ("GET", "/strategy-lab/ai-reports/{report_id}"),
    ("GET", "/strategy-lab/backtests"),
    ("GET", "/strategy-lab/backtests/{backtest_id}"),
    ("GET", "/strategy-lab/backtests/{backtest_id}/ai-reports"),
    ("GET", "/strategy-lab/backtests/{backtest_id}/drawdowns"),
    ("GET", "/strategy-lab/backtests/{backtest_id}/equity-curve"),
    ("GET", "/strategy-lab/backtests/{backtest_id}/quality-summary"),
    ("GET", "/strategy-lab/backtests/{backtest_id}/results"),
    ("GET", "/strategy-lab/backtests/{backtest_id}/trades"),
    ("GET", "/strategy-lab/backtests/{backtest_id}/walk-forward"),
    ("GET", "/strategy-lab/comparisons"),
    ("GET", "/strategy-lab/comparisons/{backtest_run_id}"),
    ("GET", "/strategy-lab/configs"),
    ("GET", "/strategy-lab/configs/{config_id}"),
    ("GET", "/strategy-lab/cost-model/profiles"),
    ("GET", "/strategy-lab/cost-model/stress-presets"),
    ("GET", "/trading/halt"),
    ("GET", "/trading/halt/status"),
    # --- PATCH ---
    ("PATCH", "/baseline-candidates/{candidate_id}"),
    ("PATCH", "/models/{model_version_id}"),
    ("PATCH", "/paper-validation/plans/{plan_id}"),
    ("PATCH", "/paper/recommendations/{recommendation_id}/review"),
    ("PATCH", "/risk/limits/{config_id}"),
    # --- POST ---
    ("POST", "/approvals/alerts/notifications/{notification_id}/read"),
    ("POST", "/approvals/alerts/rules"),
    ("POST", "/approvals/alerts/rules/{rule_id}/acknowledge"),
    ("POST", "/approvals/alerts/rules/{rule_id}/snooze"),
    ("POST", "/approvals/create"),
    ("POST", "/approvals/{request_id}/approve"),
    ("POST", "/approvals/{request_id}/execute"),
    ("POST", "/approvals/{request_id}/expire"),
    ("POST", "/approvals/{request_id}/reject"),
    ("POST", "/assets"),
    ("POST", "/baseline-candidates"),
    ("POST", "/baseline-candidates/{candidate_id}/reject"),
    ("POST", "/broker/daily-pnl/snapshot"),
    ("POST", "/broker/daily-pnl/snapshot/scheduled"),
    ("POST", "/broker/orders"),
    ("POST", "/broker/orders/dry-run"),
    ("POST", "/broker/reconcile"),
    ("POST", "/broker/trades/normalize"),
    ("POST", "/cockpit/mode"),
    ("POST", "/execution/live"),
    ("POST", "/execution/paper"),
    ("POST", "/execution/paper/{execution_id}/close"),
    ("POST", "/execution/paper/{execution_id}/fill"),
    ("POST", "/execution/positions/{position_id}/snapshot"),
    ("POST", "/governance/promote"),
    ("POST", "/governance/rollback"),
    ("POST", "/market-data/auto-paper/arming"),
    ("POST", "/market-data/auto-paper/arming/disarm"),
    ("POST", "/market-data/auto-paper/kill-switch/activate"),
    ("POST", "/market-data/auto-paper/kill-switch/deactivate"),
    ("POST", "/market-data/auto-paper/run"),
    ("POST", "/market-data/auto-paper/scheduler/pause"),
    ("POST", "/market-data/auto-paper/scheduler/resume"),
    ("POST", "/market-data/sync"),
    ("POST", "/models"),
    ("POST", "/monitor/test/{service_id}"),
    ("POST", "/opportunities/sweep/run"),
    ("POST", "/options/strategies/call-spread"),
    ("POST", "/options/strategies/collar"),
    ("POST", "/options/strategies/put-spread"),
    ("POST", "/paper-validation/plans"),
    ("POST", "/paper-validation/plans/{plan_id}/evidence/manual"),
    ("POST", "/paper-validation/plans/{plan_id}/evidence/{evidence_id}/exclude"),
    ("POST", "/paper-validation/plans/{plan_id}/evidence/{evidence_id}/include"),
    ("POST", "/paper-validation/plans/{plan_id}/recalculate"),
    ("POST", "/paper-validation/plans/{plan_id}/reconcile"),
    ("POST", "/paper-validation/plans/{plan_id}/start"),
    ("POST", "/paper-validation/plans/{plan_id}/stop"),
    ("POST", "/paper/recommendations"),
    ("POST", "/prompt-adaptations/apply"),
    ("POST", "/research/data/import"),
    ("POST", "/research/data/quality/outliers/{report_id}/review"),
    ("POST", "/research/data/quality/recalculate"),
    ("POST", "/research/jobs/import"),
    ("POST", "/research/jobs/quality/recalculate"),
    ("POST", "/research/jobs/{job_id}/cancel"),
    ("POST", "/research/jobs/{job_id}/retry"),
    ("POST", "/risk/evaluate"),
    ("POST", "/risk/limits"),
    ("POST", "/risk/limits/evaluate"),
    ("POST", "/signals/generate"),
    ("POST", "/signals/mock-generate"),
    ("POST", "/strategy-lab/backtests"),
    ("POST", "/strategy-lab/backtests/{backtest_id}/ai-report"),
    ("POST", "/strategy-lab/backtests/{backtest_id}/replay"),
    ("POST", "/strategy-lab/backtests/{backtest_id}/walk-forward"),
    ("POST", "/strategy-lab/comparisons/run"),
    ("POST", "/strategy-lab/comparisons/{backtest_run_id}/label"),
    ("POST", "/strategy-lab/configs"),
    ("POST", "/trading/halt"),
    ("POST", "/trading/halt/{halt_id}/resolve"),
    ("POST", "/workflow/run"),
    # --- PUT ---
    ("PUT", "/execution/paper/{execution_id}/journal"),
}


# Subset of routes that, if changed, must trigger a hard safety review.
# These either touch broker submission or live execution paths. Pinning
# them as a separate must-exist set protects against accidental removal
# (which could mask a regression where the route silently disappears
# without the cockpit losing visibility).
SAFETY_CRITICAL_ROUTES: set[tuple[str, str]] = {
    # Broker mutating surface
    ("DELETE", "/broker/orders/{broker_order_id}"),
    ("POST", "/broker/orders"),
    ("POST", "/broker/orders/dry-run"),
    ("POST", "/broker/reconcile"),
    # Live execution surface (must remain present and gated)
    ("POST", "/execution/live"),
    # Trading halt surface (kill-switch visibility)
    ("GET", "/trading/halt"),
    ("GET", "/trading/halt/status"),
    ("POST", "/trading/halt"),
    ("POST", "/trading/halt/{halt_id}/resolve"),
    # Auto-paper kill-switch surface (must remain present)
    ("POST", "/market-data/auto-paper/kill-switch/activate"),
    ("POST", "/market-data/auto-paper/kill-switch/deactivate"),
    ("GET", "/market-data/auto-paper/kill-switch"),
    # Audit-recent endpoints (cockpit surface for the four audit logs)
    ("GET", "/broker/submit-decisions/recent"),
    ("GET", "/news-in-decision-log/recent"),
    ("GET", "/risk-decisions/recent"),
    ("GET", "/llm-logs/recent"),
}


def test_route_registry_catalog_exact_match() -> None:
    actual = _collect_method_path_pairs()
    missing = EXPECTED_ROUTES - actual
    extra = actual - EXPECTED_ROUTES
    assert not missing and not extra, (
        "FastAPI route registry drift detected. "
        f"Missing (in catalog, not in app): {sorted(missing)}. "
        f"Extra (in app, not in catalog): {sorted(extra)}. "
        "Update tests/test_route_registry_drift_lock.py::EXPECTED_ROUTES "
        "and append a build-ledger entry explaining the route change."
    )


def test_route_registry_safety_critical_routes_present() -> None:
    actual = _collect_method_path_pairs()
    missing = SAFETY_CRITICAL_ROUTES - actual
    assert not missing, (
        "Safety-critical route(s) silently removed from the FastAPI app: "
        f"{sorted(missing)}. These routes guard broker submission, live "
        "execution, the trading halt kill-switch, the auto-paper "
        "kill-switch, or the four cockpit audit surfaces. Their removal "
        "must be a deliberate, ledger-tracked phase."
    )


def test_route_registry_no_unexpected_post_to_orders() -> None:
    """Sanity floor: the only POST under /broker/orders* is the existing two."""
    actual = _collect_method_path_pairs()
    broker_order_posts = {
        (m, p) for (m, p) in actual
        if m == "POST" and p.startswith("/broker/orders")
    }
    expected = {
        ("POST", "/broker/orders"),
        ("POST", "/broker/orders/dry-run"),
    }
    assert broker_order_posts == expected, (
        f"Unexpected POST under /broker/orders*: {sorted(broker_order_posts)}. "
        "A new POST endpoint that submits orders must be paired with an "
        "explicit safety review and the SAFETY_CRITICAL_ROUTES catalog "
        "must be updated."
    )


def test_route_registry_total_count_floor() -> None:
    """Sanity floor: the app must register at least the cycle-58 baseline."""
    actual = _collect_method_path_pairs()
    assert len(actual) >= 191, (
        f"Route count fell below cycle-58 baseline of 191 (now {len(actual)}). "
        "A drop usually means a router was unintentionally unregistered."
    )
