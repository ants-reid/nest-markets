"""Drift-lock: broker submit decision timeline route + response contract.

Pins the read-only audit surface that exposes persisted broker submit
decisions to the cockpit timeline page. Renaming a filter, swapping the
response model, exposing a secret-like field, or accidentally adding a
mutation route on this prefix would silently break or weaken the audit
guarantees of the timeline.

Drift-lock notes:
    * Test-only / additive; no production code change.
    * The route remains read-only (GET) and the response model remains
      ``BrokerSubmitDecisionsResponseSchema``.
    * Auto trading, live trading, and worker submit authority are
      unaffected.
"""

from __future__ import annotations

import inspect
from typing import Any

from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.api.routes import broker_submit_decisions as route_module
from app.schemas.broker_schemas import (
    BrokerSubmitDecisionMessageSchema,
    BrokerSubmitDecisionRequestSummarySchema,
    BrokerSubmitDecisionRowSchema,
    BrokerSubmitDecisionsFiltersSchema,
    BrokerSubmitDecisionsResponseSchema,
)


# ── route surface pins ──────────────────────────────────────────────────

EXPECTED_PREFIX = "/broker"
EXPECTED_PATH = "/broker/submit-decisions/recent"
EXPECTED_METHOD = "GET"
EXPECTED_RESPONSE_MODEL = "BrokerSubmitDecisionsResponseSchema"
EXPECTED_FILTER_PARAMS: frozenset[str] = frozenset(
    {
        "limit",
        "intent",
        "would_block",
        "source",
        "decision_status",
        "correlation_id",
        "recommendation_id",
    }
)


def _timeline_route() -> APIRoute:
    for r in route_module.router.routes:
        if isinstance(r, APIRoute) and r.path == EXPECTED_PATH:
            return r
    raise AssertionError(
        f"Timeline route {EXPECTED_PATH!r} not found on router; "
        "the read-only audit surface has been moved or removed."
    )


def test_router_prefix_unchanged() -> None:
    assert route_module.router.prefix == EXPECTED_PREFIX, (
        f"broker_submit_decisions router prefix drifted: "
        f"expected {EXPECTED_PREFIX!r}, got {route_module.router.prefix!r}."
    )


def test_timeline_route_is_get_only() -> None:
    route = _timeline_route()
    assert route.methods == {EXPECTED_METHOD}, (
        f"Timeline route methods drifted: expected {{'GET'}}, "
        f"got {route.methods!r}. Read-only audit guarantee broken."
    )


def test_no_mutation_route_on_submit_decisions_prefix() -> None:
    """No POST/PUT/PATCH/DELETE may exist anywhere under the
    /broker/submit-decisions* prefix on this router. The persisted
    decision feed is append-only and the read endpoint must never
    grow a sibling mutation surface."""
    forbidden = {"POST", "PUT", "PATCH", "DELETE"}
    violations: list[str] = []
    for r in route_module.router.routes:
        if not isinstance(r, APIRoute):
            continue
        if "/submit-decisions" not in r.path:
            continue
        bad = r.methods & forbidden
        if bad:
            violations.append(f"{sorted(bad)} {r.path}")
    assert not violations, (
        "Mutation route(s) appeared under /broker/submit-decisions*: "
        f"{violations}. The decision feed must remain append-only and "
        "the read endpoint must never grow a sibling mutation surface."
    )


def test_timeline_response_model_binding_unchanged() -> None:
    route = _timeline_route()
    rm = route.response_model
    assert rm is BrokerSubmitDecisionsResponseSchema, (
        f"Timeline response_model drifted: expected "
        f"{EXPECTED_RESPONSE_MODEL}, got {getattr(rm, '__name__', rm)!r}."
    )


def test_timeline_handler_filter_signature_unchanged() -> None:
    sig = inspect.signature(route_module.list_recent_broker_submit_decisions)
    params = set(sig.parameters.keys())
    missing = EXPECTED_FILTER_PARAMS - params
    extra = params - EXPECTED_FILTER_PARAMS
    msgs: list[str] = []
    if missing:
        msgs.append(f"  Missing filter param(s): {sorted(missing)}")
    if extra:
        msgs.append(f"  Unexpected new filter param(s): {sorted(extra)}")
    assert not msgs, (
        "Timeline handler filter signature drifted. The cockpit timeline "
        "depends on this exact filter set:\n" + "\n".join(msgs)
    )


# ── response schema field-catalog pins ──────────────────────────────────

EXPECTED_ROW_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "created_at",
        "signal_id",
        "intent",
        "would_block",
        "blocked_reason_code",
        "blocked_reason_text",
        "decision_status",
        "allowed_to_submit",
        "decision_reason",
        "source",
        "submit_gate",
        "broker_order_id",
        "correlation_id",
        "recommendation_id",
        "route_check_reference",
        "dry_run_reference",
        "execution_mode",
        "account_mode",
        "risk_profile_id",
        "risk_block_reason",
        "execution_source",
        "serious_paper_source",
        "canonical_paper_route",
        "broker_account_mode",
        "live_state",
        "request_summary",
        "warnings",
        "blocked_reasons",
        "preflight_json",
    }
)

EXPECTED_RESPONSE_FIELDS: frozenset[str] = frozenset(
    {"count", "limit", "filters", "advisory", "items"}
)

EXPECTED_FILTERS_FIELDS: frozenset[str] = frozenset(
    {
        "intent",
        "would_block",
        "source",
        "decision_status",
        "correlation_id",
        "recommendation_id",
    }
)

EXPECTED_REQUEST_SUMMARY_FIELDS: frozenset[str] = frozenset(
    {"ticker", "side", "quantity", "order_type", "limit_price", "stop_price"}
)

EXPECTED_MESSAGE_FIELDS: frozenset[str] = frozenset(
    {"code", "message", "source", "classification", "severity"}
)

# Substrings that would indicate a credential/secret leaked into the
# wire shape. These must NEVER appear as a field name on the timeline
# response models.
FORBIDDEN_SECRET_SUBSTRINGS: tuple[str, ...] = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "private_key",
    "private-key",
    "account_password",
    "credential",
)


def _check_field_catalog(
    cls: type[BaseModel], expected: frozenset[str]
) -> list[str]:
    actual = frozenset(cls.model_fields.keys())
    extra = actual - expected
    missing = expected - actual
    out: list[str] = []
    if extra:
        out.append(f"  Unexpected new field(s): {sorted(extra)}")
    if missing:
        out.append(f"  Missing expected field(s): {sorted(missing)}")
    return out


def test_timeline_row_field_catalog_exact() -> None:
    msgs = _check_field_catalog(
        BrokerSubmitDecisionRowSchema, EXPECTED_ROW_FIELDS
    )
    assert not msgs, (
        "BrokerSubmitDecisionRowSchema field catalog drifted. The "
        "cockpit timeline reads these exact fields:\n" + "\n".join(msgs)
    )


def test_timeline_response_field_catalog_exact() -> None:
    msgs = _check_field_catalog(
        BrokerSubmitDecisionsResponseSchema, EXPECTED_RESPONSE_FIELDS
    )
    assert not msgs, (
        "BrokerSubmitDecisionsResponseSchema field catalog drifted:\n"
        + "\n".join(msgs)
    )


def test_timeline_filters_field_catalog_exact() -> None:
    msgs = _check_field_catalog(
        BrokerSubmitDecisionsFiltersSchema, EXPECTED_FILTERS_FIELDS
    )
    assert not msgs, (
        "BrokerSubmitDecisionsFiltersSchema field catalog drifted:\n"
        + "\n".join(msgs)
    )


def test_timeline_request_summary_field_catalog_exact() -> None:
    msgs = _check_field_catalog(
        BrokerSubmitDecisionRequestSummarySchema,
        EXPECTED_REQUEST_SUMMARY_FIELDS,
    )
    assert not msgs, (
        "BrokerSubmitDecisionRequestSummarySchema field catalog drifted:\n"
        + "\n".join(msgs)
    )


def test_timeline_message_field_catalog_exact() -> None:
    msgs = _check_field_catalog(
        BrokerSubmitDecisionMessageSchema, EXPECTED_MESSAGE_FIELDS
    )
    assert not msgs, (
        "BrokerSubmitDecisionMessageSchema field catalog drifted:\n"
        + "\n".join(msgs)
    )


def test_no_secret_like_fields_on_any_timeline_schema() -> None:
    timeline_schemas: tuple[type[BaseModel], ...] = (
        BrokerSubmitDecisionRowSchema,
        BrokerSubmitDecisionsResponseSchema,
        BrokerSubmitDecisionsFiltersSchema,
        BrokerSubmitDecisionRequestSummarySchema,
        BrokerSubmitDecisionMessageSchema,
    )
    leaks: list[str] = []
    for cls in timeline_schemas:
        for field_name in cls.model_fields.keys():
            lowered = field_name.lower()
            for bad in FORBIDDEN_SECRET_SUBSTRINGS:
                if bad in lowered:
                    leaks.append(f"  {cls.__name__}.{field_name} (matches {bad!r})")
    assert not leaks, (
        "Secret-like field name(s) appeared on the timeline wire "
        "contract. Audit feeds must NEVER expose credential surfaces:\n"
        + "\n".join(leaks)
    )


def test_handler_advisory_documents_append_only_posture() -> None:
    """The route module's own docstring must keep advertising the
    read-only + append-only audit posture; a silent rewrite that
    removed those promises would be a real surface change."""
    doc = (route_module.__doc__ or "").lower()
    assert "read-only" in doc or "read only" in doc, (
        "broker_submit_decisions module docstring no longer advertises "
        "the read-only posture."
    )
    handler_doc = (
        route_module.list_recent_broker_submit_decisions.__doc__ or ""
    ).lower()
    assert "never modifies state" in handler_doc, (
        "Timeline handler docstring no longer promises 'never modifies state'; "
        "this is the audit guarantee that the cockpit relies on."
    )


def test_timeline_handler_does_not_import_submit_seams() -> None:
    """The read-only audit route module must not import any broker
    submission seam. If it ever did, it could be silently turned into
    a mutation surface in a future edit."""
    forbidden: tuple[str, ...] = (
        "submit_order",
        "submit_auto_order",
        "_submit_order_for_intent",
        "BrokerService",
    )
    module_globals: dict[str, Any] = vars(route_module)
    leaks = [name for name in forbidden if name in module_globals]
    assert not leaks, (
        f"broker_submit_decisions route module imported submit seam(s) "
        f"{leaks}. The audit feed module must never import any broker "
        "submission entrypoint."
    )
