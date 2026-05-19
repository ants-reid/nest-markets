"""Drift-lock: audit_log_service payload-key catalog (cycle 69).

Pins the LITERAL keys of the JSON payload dict that each safety
audit function writes to ``_AUDIT_LOG_PATH``. Renaming
``"idempotency_key"`` to ``"key"`` in the payload would silently
break every downstream audit-row consumer (e.g. cockpit views) even
though the function signature still accepts the kwarg.

Strategy: monkey-patch ``audit_log_service._append`` to capture the
event dict instead of writing to disk; assert key set.

Test-only / additive.
"""

from __future__ import annotations

from app.services import audit_log_service

EXPECTED_TRADE_SUBMITTED_KEYS: frozenset[str] = frozenset(
    {"ts", "event", "endpoint", "asset", "side", "qty", "notional",
     "idempotency_key"}
)
EXPECTED_TRADE_SUBMITTED_EVENT = "trade_submitted"

EXPECTED_WORKFLOW_RUN_KEYS: frozenset[str] = frozenset(
    {"ts", "event", "asset", "timeframe", "execution_mode", "outcome",
     "idempotency_key"}
)
EXPECTED_WORKFLOW_RUN_EVENT = "workflow_run"

EXPECTED_BROKER_ORDER_KEYS: frozenset[str] = frozenset(
    {"ts", "event", "action", "ticker", "side", "quantity", "status",
     "broker_order_id", "reason", "dry_run", "issues"}
)
EXPECTED_BROKER_ORDER_EVENT = "broker_order_event"


class _Capture:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def __call__(self, event: dict) -> None:
        self.events.append(event)


def _patch_append(monkeypatch_target):
    cap = _Capture()
    original = audit_log_service._append
    audit_log_service._append = cap  # type: ignore[assignment]
    return cap, original


def _restore_append(original) -> None:
    audit_log_service._append = original  # type: ignore[assignment]


def test_trade_submitted_payload_keys_unchanged() -> None:
    cap, original = _patch_append(audit_log_service)
    try:
        audit_log_service.log_trade_submitted(
            endpoint="/execution/paper",
            asset="AAPL",
            side="long",
            qty=1.0,
            notional=100.0,
            idempotency_key="abc",
        )
    finally:
        _restore_append(original)
    assert len(cap.events) == 1
    event = cap.events[0]
    assert event["event"] == EXPECTED_TRADE_SUBMITTED_EVENT
    actual_keys = frozenset(event.keys())
    assert actual_keys == EXPECTED_TRADE_SUBMITTED_KEYS, (
        "log_trade_submitted payload key drift.\n"
        f"  expected: {sorted(EXPECTED_TRADE_SUBMITTED_KEYS)}\n"
        f"  actual:   {sorted(actual_keys)}\n"
        "If intentional, update EXPECTED_TRADE_SUBMITTED_KEYS and "
        "audit every downstream consumer of the audit log."
    )


def test_workflow_run_payload_keys_unchanged() -> None:
    cap, original = _patch_append(audit_log_service)
    try:
        audit_log_service.log_workflow_run(
            asset="AAPL",
            timeframe="1d",
            execution_mode="paper",
            outcome="approved",
            idempotency_key="abc",
        )
    finally:
        _restore_append(original)
    assert len(cap.events) == 1
    event = cap.events[0]
    assert event["event"] == EXPECTED_WORKFLOW_RUN_EVENT
    actual_keys = frozenset(event.keys())
    assert actual_keys == EXPECTED_WORKFLOW_RUN_KEYS, (
        "log_workflow_run payload key drift.\n"
        f"  expected: {sorted(EXPECTED_WORKFLOW_RUN_KEYS)}\n"
        f"  actual:   {sorted(actual_keys)}"
    )


def test_broker_order_event_payload_keys_unchanged() -> None:
    cap, original = _patch_append(audit_log_service)
    try:
        audit_log_service.log_broker_order_event(
            action="submit",
            ticker="AAPL",
            side="BUY",
            quantity=1.0,
            status="submitted",
            broker_order_id="x",
            reason=None,
            dry_run=False,
        )
    finally:
        _restore_append(original)
    assert len(cap.events) == 1
    event = cap.events[0]
    assert event["event"] == EXPECTED_BROKER_ORDER_EVENT
    actual_keys = frozenset(event.keys())
    assert actual_keys == EXPECTED_BROKER_ORDER_KEYS, (
        "log_broker_order_event payload key drift.\n"
        f"  expected: {sorted(EXPECTED_BROKER_ORDER_KEYS)}\n"
        f"  actual:   {sorted(actual_keys)}"
    )
