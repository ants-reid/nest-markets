"""Drift-lock: pin the response shape of the four cockpit audit endpoints.

Cycle 58 — MH-DRIFTLOCK-AUDIT-RESPONSE-SHAPE (pure additive test-only).

Endpoints pinned
----------------
* ``GET /broker/submit-decisions/recent``
* ``GET /news-in-decision-log/recent``
* ``GET /risk-decisions/recent``
* ``GET /llm-logs/recent``

Why
---
These four endpoints are the cockpit's audit-trail surface. Their
response shapes are consumed by frontend tiles and human operators. A
silent removal or rename of an item-key (``would_block``, ``approved``,
``evidence_class``, ``error_class``, ...) would degrade safety
attribution without producing a runtime exception — exactly the class
of drift the lock exists to catch.

How the pin works
-----------------
The handler modules construct the per-row response dicts inside their
local ``_serialize`` function. Rather than seeding the database, this
test inspects ``inspect.getsource(_serialize)`` and asserts that every
expected ``"key":`` substring is present. This catches both removals
(key disappears) and accidental renames.

Top-level response keys are pinned as a hard-coded set per endpoint.
The handler return-dict is built as a literal expression at the end of
each route function, so the same source-introspection technique works.

Drift-lock guarantees
---------------------
* Read-only test — no DB access, no HTTP calls.
* Auto-paper enforcement remains OFF.
* Auto trading remains OFF.
* Live trading remains OFF.
* ``assert_auto_trading_allowed()`` is unchanged.
"""

from __future__ import annotations

import inspect

from app.api.routes import (
    broker_submit_decisions as broker_submit_decisions_module,
)
from app.api.routes import llm_logs as llm_logs_module
from app.api.routes import news_in_decision_log as news_in_decision_log_module
from app.api.routes import risk_decisions as risk_decisions_module


# Per-endpoint expected item dict keys (what each row in `items[]` MUST
# contain). These are pinned by inspecting the source of `_serialize`.
EXPECTED_BROKER_SUBMIT_ITEM_KEYS: set[str] = {
    "id",
    "created_at",
    "signal_id",
    "intent",
    "would_block",
    "blocked_reason_code",
    "blocked_reason_text",
    "preflight_json",
}

EXPECTED_NEWS_IN_DECISION_LOG_ITEM_KEYS: set[str] = {
    "id",
    "created_at",
    "decision_kind",
    "decision_id",
    "signal_id",
    "llm_request_log_id",
    "news_article_id",
    "news_item_id",
    "evidence_class",
    "headline_snapshot",
    "source_snapshot",
    "url_snapshot",
    "published_at_snapshot",
    "context_json",
}

EXPECTED_RISK_DECISIONS_ITEM_KEYS: set[str] = {
    "id",
    "created_at",
    "timestamp",
    "signal_id",
    "approved",
    "blocking_rule",
    "block_reason_code",
    "risk_profile_id",
    "position_risk_pct",
    "notional_allowed",
    "correlation_bucket",
    "spread_ok",
    "session_ok",
    "drawdown_ok",
    "cooldown_ok",
    "kill_switch_active",
    "blocked_reasons_json",
}

EXPECTED_LLM_LOGS_ITEM_KEYS: set[str] = {
    "id",
    "created_at",
    "started_at",
    "provider",
    "model_requested",
    "model_returned",
    "system_prompt_hash",
    "user_prompt_hash",
    "system_prompt_preview",
    "user_prompt_preview",
    "prompt_version_id",
    "stop_reason",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "latency_ms",
    "error_class",
    "error_message",
    "correlation_id",
    "response_payload_preview",
}

# Subset of keys that are SAFETY-attribution critical: removal would silently
# erase the operator's ability to detect a wrongly-permitted intent.
SAFETY_ATTRIBUTION_KEYS: dict[str, set[str]] = {
    "broker_submit_decisions": {
        "intent",
        "would_block",
        "blocked_reason_code",
        "signal_id",
    },
    "news_in_decision_log": {
        "decision_kind",
        "evidence_class",
        "signal_id",
    },
    "risk_decisions": {
        "approved",
        "blocking_rule",
        "block_reason_code",
        "kill_switch_active",
        "signal_id",
    },
    "llm_logs": {
        "provider",
        "error_class",
        "correlation_id",
        "system_prompt_hash",
        "user_prompt_hash",
    },
}


def _assert_keys_in_serialize_source(
    module, expected_keys: set[str], endpoint_label: str
) -> None:
    src = inspect.getsource(module._serialize)
    missing = sorted(k for k in expected_keys if f'"{k}":' not in src)
    assert not missing, (
        f"Endpoint '{endpoint_label}': item keys missing from "
        f"_serialize() source: {missing}. The cockpit and ledger "
        "depend on these keys; their removal must be a deliberate, "
        "ledger-tracked phase. If the rename was intentional, update "
        "tests/test_audit_response_shape_drift_lock.py and append a "
        "build-ledger entry explaining the contract change."
    )


def test_broker_submit_decisions_item_keys_pinned() -> None:
    _assert_keys_in_serialize_source(
        broker_submit_decisions_module,
        EXPECTED_BROKER_SUBMIT_ITEM_KEYS,
        "GET /broker/submit-decisions/recent",
    )


def test_news_in_decision_log_item_keys_pinned() -> None:
    _assert_keys_in_serialize_source(
        news_in_decision_log_module,
        EXPECTED_NEWS_IN_DECISION_LOG_ITEM_KEYS,
        "GET /news-in-decision-log/recent",
    )


def test_risk_decisions_item_keys_pinned() -> None:
    _assert_keys_in_serialize_source(
        risk_decisions_module,
        EXPECTED_RISK_DECISIONS_ITEM_KEYS,
        "GET /risk-decisions/recent",
    )


def test_llm_logs_item_keys_pinned() -> None:
    _assert_keys_in_serialize_source(
        llm_logs_module,
        EXPECTED_LLM_LOGS_ITEM_KEYS,
        "GET /llm-logs/recent",
    )


def test_safety_attribution_keys_present_in_source() -> None:
    """Hard-pin: safety-attribution keys must literally appear in source."""
    pairs = [
        (broker_submit_decisions_module, "broker_submit_decisions"),
        (news_in_decision_log_module, "news_in_decision_log"),
        (risk_decisions_module, "risk_decisions"),
        (llm_logs_module, "llm_logs"),
    ]
    for module, label in pairs:
        src = inspect.getsource(module._serialize)
        required = SAFETY_ATTRIBUTION_KEYS[label]
        missing = sorted(k for k in required if f'"{k}":' not in src)
        assert not missing, (
            f"SAFETY-attribution key(s) missing from {label} _serialize: "
            f"{missing}. These keys are how the cockpit attributes WHY a "
            "trading decision was blocked or permitted; their removal "
            "would silently degrade safety attribution."
        )


def test_top_level_response_keys_present() -> None:
    """Pin the top-level response dict keys for each endpoint.

    Every endpoint returns a dict with at minimum: count, limit, filters,
    items. Three of the four also include an 'advisory' string. We pin the
    shared minimum here.
    """
    common_keys = {"count", "limit", "filters", "items"}
    handlers = [
        (
            broker_submit_decisions_module.list_recent_broker_submit_decisions,
            "GET /broker/submit-decisions/recent",
        ),
        (
            news_in_decision_log_module.list_recent_news_in_decision_log,
            "GET /news-in-decision-log/recent",
        ),
        (
            risk_decisions_module.list_recent_risk_decisions,
            "GET /risk-decisions/recent",
        ),
        (
            llm_logs_module.list_recent_llm_logs,
            "GET /llm-logs/recent",
        ),
    ]
    for handler, label in handlers:
        src = inspect.getsource(handler)
        missing = sorted(k for k in common_keys if f'"{k}":' not in src)
        assert not missing, (
            f"Endpoint '{label}': required top-level response key(s) "
            f"missing from handler source: {missing}."
        )
