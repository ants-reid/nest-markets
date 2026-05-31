"""Drift-lock: forbid secret-like field names on cockpit audit feed schemas.

Cycle 64 — MH-DRIFTLOCK-AUDIT-FEED-NO-SECRET.

Why this pin exists
-------------------
Cycle 63 added explicit ``response_model=`` bindings on the four sibling
cockpit audit feeds (``risk_decisions``, ``news_in_decision_log``,
``llm_logs``, ``monitor_worker_run_log``). The new envelopes mirror the
existing ``_serialize`` output, which is already redaction-aware. This
pin freezes the field-name surface area so a future schema addition
cannot silently re-introduce a credential-shaped field.

The forbidden set is deliberately narrow: exact lower-case field-name
matches for credential-grade identifiers. Audit-relevant fields like
``user_prompt_preview`` or ``system_prompt_hash`` are explicitly NOT
forbidden — they are length-capped previews / one-way hashes that the
LLM round-trip surface already redacts at write time.

Drift-lock guarantees
---------------------
* Test-only, additive. Zero production-code change.
* No DB access, no HTTP calls, no network.
* Auto-paper enforcement, auto trading, and live trading remain OFF.
"""

from __future__ import annotations

from app.schemas.audit_feeds import (
    LlmLogAuditFiltersSchema,
    LlmLogAuditResponseSchema,
    LlmLogAuditRowSchema,
    NewsInDecisionLogAuditFiltersSchema,
    NewsInDecisionLogAuditResponseSchema,
    NewsInDecisionLogAuditRowSchema,
    RiskDecisionAuditFiltersSchema,
    RiskDecisionAuditResponseSchema,
    RiskDecisionAuditRowSchema,
    WorkerRunLogEntrySchema,
    WorkerRunLogOverviewResponseSchema,
    WorkerRunLogRetentionSchema,
    WorkerRunLogTotalsSchema,
)

# Exact-match credential-shaped field names that must never appear on
# any cockpit audit feed schema. Extend with care; any addition is a
# real safety tightening.
_FORBIDDEN_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "secret_key",
        "client_secret",
        "api_key",
        "api_token",
        "access_token",
        "refresh_token",
        "bearer_token",
        "authorization",
        "auth_token",
        "private_key",
        "ssh_key",
        "session_token",
        "cookie",
        "set_cookie",
    }
)

# All audit-feed schema classes whose field names this pin covers.
_AUDIT_FEED_SCHEMAS = (
    RiskDecisionAuditRowSchema,
    RiskDecisionAuditFiltersSchema,
    RiskDecisionAuditResponseSchema,
    NewsInDecisionLogAuditRowSchema,
    NewsInDecisionLogAuditFiltersSchema,
    NewsInDecisionLogAuditResponseSchema,
    LlmLogAuditRowSchema,
    LlmLogAuditFiltersSchema,
    LlmLogAuditResponseSchema,
    WorkerRunLogEntrySchema,
    WorkerRunLogRetentionSchema,
    WorkerRunLogTotalsSchema,
    WorkerRunLogOverviewResponseSchema,
)


def _schema_field_names(model_cls: type) -> set[str]:
    return set(model_cls.model_fields.keys())


def test_audit_feed_schemas_have_no_secret_field_names() -> None:
    violations: list[str] = []
    for schema_cls in _AUDIT_FEED_SCHEMAS:
        for field_name in _schema_field_names(schema_cls):
            if field_name.lower() in _FORBIDDEN_FIELD_NAMES:
                violations.append(
                    f"  {schema_cls.__name__}.{field_name} "
                    "matches the credential-shaped forbidden set"
                )
    assert not violations, (
        "Cockpit audit feed schemas must not expose credential-shaped "
        "field names. The four read-only audit feeds "
        "(risk_decisions, news_in_decision_log, llm_logs, "
        "monitor_worker_run_log) are operator-facing and must never "
        "echo passwords, tokens, keys, or authorization headers. "
        "If a new field is genuinely safe, choose a non-credential "
        "name; otherwise drop it.\n"
        + "\n".join(violations)
    )


def test_audit_feed_schemas_cover_expected_envelope_keys() -> None:
    """Pin the top-level envelope key set for each audit-feed response.

    Catches accidental key drift (e.g. ``count`` -> ``size``) that would
    silently break the cockpit tile contract.
    """
    expected: dict[type, set[str]] = {
        RiskDecisionAuditResponseSchema: {
            "count",
            "limit",
            "filters",
            "advisory",
            "items",
        },
        NewsInDecisionLogAuditResponseSchema: {
            "count",
            "limit",
            "filters",
            "advisory",
            "items",
        },
        LlmLogAuditResponseSchema: {
            "count",
            "limit",
            "filters",
            "items",
        },
        WorkerRunLogOverviewResponseSchema: {
            "advisory",
            "limit",
            "retention",
            "totals",
            "entries",
        },
    }
    drift: list[str] = []
    for schema_cls, expected_keys in expected.items():
        actual = _schema_field_names(schema_cls)
        missing = expected_keys - actual
        extra = actual - expected_keys
        if missing or extra:
            drift.append(
                f"  {schema_cls.__name__}: missing={sorted(missing)} "
                f"extra={sorted(extra)}"
            )
    assert not drift, (
        "Audit-feed envelope key drift detected. Cockpit tiles consume "
        "these keys directly; any change must be a deliberate, "
        "ledger-tracked phase.\n"
        + "\n".join(drift)
    )
