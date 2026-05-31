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

import hashlib
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


# ── source/body SHA pins ────────────────────────────────────────────────
#
# Pin the exact source of the read-only timeline handler and its
# frontend client helper. Any intentional edit must rehash and update
# the constants below, which forces a deliberate drift-lock review that
# the route remains read-only and the client remains GET-only.

_EXPECTED_HANDLER_SHA = (
    "6789b6fea09bfec63e4518e9e033ab0acd15f76a3753c0a8e743f39fec2c014f"
)
_EXPECTED_HANDLER_LEN = 2716

_EXPECTED_CLIENT_HELPER_SHA = (
    "e0286e79d78541ecc6f4f5470011a74008e85b9bc2a1f31125f981a28c89fe56"
)
_EXPECTED_CLIENT_HELPER_LEN = 1209

# Repo root: tests/<f>.py -> tests -> apps/api -> apps -> repo
import re as _re  # noqa: E402  (local import; only used by helper hash test)
from pathlib import Path as _Path  # noqa: E402

_REPO_ROOT = _Path(__file__).resolve().parents[3]
_CLIENT_HELPER_PATH = (
    _REPO_ROOT / "apps" / "web" / "lib" / "api" / "brokerSubmitDecisions.ts"
)


def _hash_source(src: str) -> tuple[str, int]:
    return hashlib.sha256(src.encode("utf-8")).hexdigest(), len(src)


def _extract_get_recent_helper_body() -> str:
    """Return the exact text of the ``getRecentBrokerSubmitDecisions``
    declaration, from ``export async function`` through the matching
    closing brace. Brace counting starts at the body-opening ``{``
    (which follows ``): Promise<...> {``), so the ``= {}`` default in
    the parameter list does not confuse the scan."""
    text = _CLIENT_HELPER_PATH.read_text(encoding="utf-8")
    start = text.index("export async function getRecentBrokerSubmitDecisions")
    m = _re.search(r"\): Promise<[^>]+> \{", text[start:])
    assert m is not None, (
        "Could not locate getRecentBrokerSubmitDecisions body-opening "
        "brace; the client helper signature has changed shape."
    )
    brace_open = start + m.end() - 1
    depth = 1
    j = brace_open + 1
    while depth > 0 and j < len(text):
        c = text[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        j += 1
    assert depth == 0, (
        "Unbalanced braces while extracting getRecentBrokerSubmitDecisions; "
        "the client helper is malformed."
    )
    return text[start:j]


def test_submit_decisions_recent_handler_body_hash_is_pinned() -> None:
    """SHA-pin the body of the read-only timeline handler.

    If this fails because of an intentional edit, recompute the hash::

        cd apps/api
        .venv/bin/python -c 'import hashlib, inspect; \
            from app.api.routes import broker_submit_decisions as m; \
            s = inspect.getsource(m.list_recent_broker_submit_decisions); \
            print(hashlib.sha256(s.encode()).hexdigest(), len(s))'

    Then update ``_EXPECTED_HANDLER_SHA`` / ``_EXPECTED_HANDLER_LEN``
    AFTER confirming the handler remains read-only (no INSERT/UPDATE/
    DELETE, no broker submit call, no risk-control relaxation).
    """
    src = inspect.getsource(route_module.list_recent_broker_submit_decisions)
    sha, length = _hash_source(src)
    assert sha == _EXPECTED_HANDLER_SHA and length == _EXPECTED_HANDLER_LEN, (
        "Timeline handler body drift: expected "
        f"sha256={_EXPECTED_HANDLER_SHA} len={_EXPECTED_HANDLER_LEN}; "
        f"got sha256={sha} len={length}. "
        "Re-verify the handler is still read-only before updating the pin."
    )


def test_submit_decisions_timeline_client_helper_body_hash_is_pinned() -> None:
    """SHA-pin the body of the frontend timeline client helper.

    If this fails because of an intentional edit, recompute the hash::

        cd <repo root>
        .venv/bin/python apps/api/tests/_compute_helper_hash.py  # or
        # inline the _extract_get_recent_helper_body logic in a REPL.

    Then update ``_EXPECTED_CLIENT_HELPER_SHA`` /
    ``_EXPECTED_CLIENT_HELPER_LEN`` AFTER confirming the helper remains
    GET-only and still calls ``/broker/submit-decisions/recent``.
    """
    body = _extract_get_recent_helper_body()
    sha, length = _hash_source(body)
    assert sha == _EXPECTED_CLIENT_HELPER_SHA and length == _EXPECTED_CLIENT_HELPER_LEN, (
        "Timeline client helper body drift: expected "
        f"sha256={_EXPECTED_CLIENT_HELPER_SHA} len={_EXPECTED_CLIENT_HELPER_LEN}; "
        f"got sha256={sha} len={length}. "
        "Re-verify the helper is still GET-only and still targets "
        "/broker/submit-decisions/recent before updating the pin."
    )
