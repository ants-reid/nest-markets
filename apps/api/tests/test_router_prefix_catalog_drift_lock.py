"""Drift-lock: pin every router prefix and tag set, plus the include_router
order in app.main.

Cycle 59 — MH-DRIFTLOCK-ROUTER-PREFIX-CATALOG (pure additive test-only).

Why
---
Cycle 58's route registry pin catches add/remove/rename of individual
``(method, path)`` pairs. This file catches a different drift mode: a
router being silently re-mounted under a different prefix (e.g.
``/broker`` -> ``/broker-v2``), or a router being unregistered from
``app.main.create_app``. Either would change the cockpit's wire
contract while individual route paths remain valid relative to the new
mount.

Pinned facts
------------
* For each router module under ``app.api.routes``: ``(prefix, tags)``.
* The full set of router module names included by
  ``app.main.create_app`` (extracted from the source, not from runtime,
  so the test does not depend on side-effecting startup).

Drift-lock guarantees
---------------------
* Read-only test — does not start the app, no DB, no HTTP.
* Auto-paper enforcement remains OFF.
* Auto trading remains OFF.
* Live trading remains OFF.
* ``assert_auto_trading_allowed()`` is unchanged.
"""

from __future__ import annotations

import importlib
import inspect

# (module_path, expected_prefix, expected_tags_tuple).
# Captured at cycle 59. Tags are stored as tuples for set membership.
EXPECTED_ROUTER_CATALOG: dict[str, tuple[str, tuple[str, ...]]] = {
    "app.api.routes.approvals":               ("/approvals", ("approvals",)),
    "app.api.routes.asset_cards":             ("/asset-cards", ("asset-cards",)),
    "app.api.routes.assets":                  ("/assets", ("assets",)),
    "app.api.routes.baseline_candidates":     ("/baseline-candidates", ("baseline_candidates",)),
    "app.api.routes.broker":                  ("/broker", ("broker",)),
    "app.api.routes.broker_submit_decisions": ("/broker", ("broker-submit-decisions",)),
    "app.api.routes.cockpit_auto_paper_status": ("/cockpit", ("cockpit",)),
    "app.api.routes.cockpit_eod_report":     ("/cockpit", ("cockpit",)),
    "app.api.routes.cockpit_in_flight_adjustments": ("/cockpit", ("cockpit",)),
    "app.api.routes.cockpit_trade_close_explanations": ("/cockpit", ("cockpit",)),
    "app.api.routes.cockpit_mode":           ("/cockpit", ("cockpit",)),
    "app.api.routes.cockpit_notifications":   ("/cockpit", ("cockpit",)),
    "app.api.routes.evals":                   ("/evals", ("evals",)),
    "app.api.routes.execution":               ("/execution", ("execution",)),
    "app.api.routes.governance":              ("/governance", ("governance",)),
    "app.api.routes.health":                  ("/health", ("health",)),
    "app.api.routes.llm_logs":                ("/llm-logs", ("llm-logs",)),
    "app.api.routes.market_data":             ("/market-data", ("market-data",)),
    "app.api.routes.markets":                 ("/markets", ("markets",)),
    "app.api.routes.models":                  ("/models", ("models",)),
    "app.api.routes.monitor_feeds":          ("/monitor", ("monitor",)),
    "app.api.routes.monitor_health_history":  ("/monitor", ("monitor",)),
    "app.api.routes.monitor_incidents":       ("/monitor", ("monitor",)),
    "app.api.routes.monitor_test":            ("/monitor", ("monitor",)),
    "app.api.routes.monitor_worker_run_log":  ("/monitor", ("monitor",)),
    "app.api.routes.news_articles":           ("/news-articles", ("news-articles",)),
    "app.api.routes.news_in_decision_log":    ("/news-in-decision-log", ("news-in-decision-log",)),
    "app.api.routes.opportunities":           ("/opportunities", ("opportunities",)),
    "app.api.routes.options":                 ("/options", ("options",)),
    "app.api.routes.paper_recommendations":   ("/paper/recommendations", ("paper_recommendations",)),
    "app.api.routes.paper_validation":        ("/paper-validation", ("paper_validation",)),
    "app.api.routes.performance":             ("/performance-stats", ("performance",)),
    "app.api.routes.prompt_adaptations":      ("/prompt-adaptations", ("prompt-adaptations",)),
    "app.api.routes.prompts":                 ("/prompts", ("prompts",)),
    "app.api.routes.regime":                  ("/regime", ("regime",)),
    "app.api.routes.research_data":           ("/research/data", ("research_data",)),
    "app.api.routes.research_jobs":           ("/research/jobs", ("research_jobs",)),
    "app.api.routes.risk":                    ("/risk", ("risk",)),
    "app.api.routes.risk_decisions":          ("/risk-decisions", ("risk-decisions",)),
    "app.api.routes.risk_limits":             ("/risk/limits", ("risk_limits",)),
    "app.api.routes.scoring":                 ("/scoring", ("scoring",)),
    "app.api.routes.signals":                 ("/signals", ("signals",)),
    "app.api.routes.strategy_lab":            ("/strategy-lab", ("strategy_lab",)),
    "app.api.routes.trading_halt":            ("/trading/halt", ("trading_halt",)),
    "app.api.routes.workflow":                ("/workflow", ("workflow",)),
}

# Subset of routers whose prefix is safety-critical: re-mounting any of
# these under a different path silently breaks the cockpit's view of the
# trading-control surface.
SAFETY_CRITICAL_ROUTER_PREFIXES: dict[str, str] = {
    "app.api.routes.broker":                  "/broker",
    "app.api.routes.broker_submit_decisions": "/broker",
    "app.api.routes.execution":               "/execution",
    "app.api.routes.trading_halt":            "/trading/halt",
    "app.api.routes.risk":                    "/risk",
    "app.api.routes.risk_limits":             "/risk/limits",
    "app.api.routes.risk_decisions":          "/risk-decisions",
    "app.api.routes.news_in_decision_log":    "/news-in-decision-log",
    "app.api.routes.llm_logs":                "/llm-logs",
}


def test_router_prefix_and_tags_catalog_exact_match() -> None:
    drift: list[tuple[str, str, tuple[str, ...], str, tuple[str, ...]]] = []
    for module_path, (expected_prefix, expected_tags) in (
        EXPECTED_ROUTER_CATALOG.items()
    ):
        module = importlib.import_module(module_path)
        router = module.router
        actual_prefix = router.prefix
        actual_tags = tuple(router.tags or [])
        if actual_prefix != expected_prefix or actual_tags != expected_tags:
            drift.append(
                (module_path, expected_prefix, expected_tags,
                 actual_prefix, actual_tags)
            )
    assert not drift, (
        "Router prefix/tags drift detected: "
        f"{drift}. Update EXPECTED_ROUTER_CATALOG and append a build-"
        "ledger entry explaining the prefix/tags change."
    )


def test_safety_critical_router_prefixes_unchanged() -> None:
    drift: list[tuple[str, str, str]] = []
    for module_path, expected_prefix in SAFETY_CRITICAL_ROUTER_PREFIXES.items():
        module = importlib.import_module(module_path)
        actual = module.router.prefix
        if actual != expected_prefix:
            drift.append((module_path, expected_prefix, actual))
    assert not drift, (
        "SAFETY-critical router prefix drift: "
        f"{drift}. Re-mounting any of these routers under a different "
        "prefix would silently break the cockpit's trading-control "
        "surface. Reverse the prefix change or perform a deliberate, "
        "ledger-tracked migration."
    )


def test_create_app_includes_every_catalogued_router() -> None:
    """Source-level invariant: app.main.create_app must call
    include_router for every catalogued router (extracted by symbol).
    """
    from app import main as main_module
    src = inspect.getsource(main_module.create_app)
    missing: list[str] = []
    for module_path in EXPECTED_ROUTER_CATALOG.keys():
        # The local symbol used in main.py is e.g.
        # "approvals_router" for "app.api.routes.approvals". Extract
        # the leaf module name and append "_router".
        leaf = module_path.rsplit(".", 1)[-1]
        symbol = f"{leaf}_router"
        if f"include_router({symbol})" not in src:
            missing.append(symbol)
    assert not missing, (
        "Catalogued router(s) NOT included by app.main.create_app: "
        f"{missing}. Either add the include_router(...) call or remove "
        "the entry from EXPECTED_ROUTER_CATALOG with a ledger entry."
    )


def test_create_app_does_not_include_extra_routers() -> None:
    """Sanity floor: every ``include_router(<symbol>)`` in create_app
    corresponds to a catalogued symbol. Catches a router being added
    without updating the catalog.
    """
    from app import main as main_module
    src = inspect.getsource(main_module.create_app)
    catalogued_symbols = {
        f"{module_path.rsplit('.', 1)[-1]}_router"
        for module_path in EXPECTED_ROUTER_CATALOG.keys()
    }
    extra: list[str] = []
    for line in src.splitlines():
        line = line.strip()
        if "include_router(" not in line:
            continue
        # Form: app.include_router(<symbol>)
        head, _, tail = line.partition("include_router(")
        symbol = tail.split(")", 1)[0].split(",", 1)[0].strip()
        if symbol and symbol not in catalogued_symbols:
            extra.append(symbol)
    assert not extra, (
        "include_router(<symbol>) call(s) in create_app NOT in catalog: "
        f"{extra}. Append the new router to EXPECTED_ROUTER_CATALOG "
        "with its prefix and tags, and a build-ledger entry."
    )
