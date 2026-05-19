"""Durable trading control arming-state service.

MH-125 introduces persistence-only reads and writes for arming state. Runtime
enforcement stays outside this service until a later explicit phase wires the
control path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import TradingControlArmingState
from app.services import audit_log_service

_VALID_ARMING_STATES = {"armed", "disarmed"}
_VALID_ENABLEMENT_STATUSES = {"ready", "blocked", "warning"}
_FAIL_CLOSED_REASONS = {
    "durable_state_missing",
    "durable_state_duplicate",
    "durable_state_invalid",
    "durable_state_expired",
    "durable_state_read_failed",
}


@dataclass(frozen=True)
class TradingControlArmingAuditSummary:
    """Safe provenance summary for the latest arming audit event."""

    event_type: str
    recorded_at: datetime | None
    action: str | None
    result_status: str | None
    requested_by: str | None
    reason: str | None
    client_request_id: str | None
    arming_state_before: str | None
    arming_state_after: str | None
    failure_reasons: list[str] = field(default_factory=list)
    warning_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TradingControlArmingReadbackPosture:
    """Operator-facing diagnostic posture for durable arming state readback."""

    status: str
    arming_state: str
    scope: str
    trading_mode: str
    evaluated_at: datetime
    fail_closed_reason: str | None
    durable_row_present: bool
    duplicate_rows_detected: bool
    stored_state: str | None
    armed_at: datetime | None
    armed_by: str | None
    arm_reason: str | None
    expires_at: datetime | None
    expired: bool
    last_enablement_checked_at: datetime | None
    last_enablement_status: str | None
    last_enablement_blockers: list[str] = field(default_factory=list)
    last_enablement_warnings: list[str] = field(default_factory=list)
    client_request_id: str | None = None
    disarmed_at: datetime | None = None
    disarmed_by: str | None = None
    disarm_reason: str | None = None
    last_audit: TradingControlArmingAuditSummary | None = None


class TradingControlArmingStateService:
    """Own durable read/write state for trading-control arming posture."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _load_rows(self, *, scope: str, trading_mode: str) -> list[TradingControlArmingState]:
        return (
            self._session.query(TradingControlArmingState)
            .filter(
                TradingControlArmingState.scope == scope,
                TradingControlArmingState.trading_mode == trading_mode,
            )
            .all()
        )

    def _build_audit_summary(self) -> TradingControlArmingAuditSummary | None:
        try:
            event = audit_log_service.get_latest_auto_paper_arming_action()
        except Exception:
            return None
        if event is None:
            return None

        recorded_at: datetime | None = None
        raw_ts = event.get("ts")
        if isinstance(raw_ts, str):
            try:
                recorded_at = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            except ValueError:
                recorded_at = None

        return TradingControlArmingAuditSummary(
            event_type=str(event.get("event") or "auto_paper_arming_action"),
            recorded_at=recorded_at,
            action=event.get("action"),
            result_status=event.get("result_status"),
            requested_by=event.get("requested_by"),
            reason=event.get("reason"),
            client_request_id=event.get("client_request_id"),
            arming_state_before=event.get("arming_state_before"),
            arming_state_after=event.get("arming_state_after"),
            failure_reasons=list(event.get("failure_reasons") or []),
            warning_codes=list(event.get("warning_codes") or []),
        )

    def _build_readback_posture(
        self,
        *,
        evaluated_at: datetime,
        scope: str,
        trading_mode: str,
        row: TradingControlArmingState | None,
        status: str,
        arming_state: str,
        fail_closed_reason: str | None,
        durable_row_present: bool,
        duplicate_rows_detected: bool,
    ) -> TradingControlArmingReadbackPosture:
        expired = row is not None and row.expires_at is not None and row.expires_at <= evaluated_at
        return TradingControlArmingReadbackPosture(
            status=status,
            arming_state=arming_state,
            scope=scope,
            trading_mode=trading_mode,
            evaluated_at=evaluated_at,
            fail_closed_reason=fail_closed_reason,
            durable_row_present=durable_row_present,
            duplicate_rows_detected=duplicate_rows_detected,
            stored_state=row.state if row is not None else None,
            armed_at=row.armed_at if row is not None else None,
            armed_by=row.armed_by if row is not None else None,
            arm_reason=row.arm_reason if row is not None else None,
            expires_at=row.expires_at if row is not None else None,
            expired=expired,
            last_enablement_checked_at=row.last_enablement_checked_at if row is not None else None,
            last_enablement_status=row.last_enablement_status if row is not None else None,
            last_enablement_blockers=list(row.last_enablement_blockers or []) if row is not None else [],
            last_enablement_warnings=list(row.last_enablement_warnings or []) if row is not None else [],
            client_request_id=row.client_request_id if row is not None else None,
            disarmed_at=row.disarmed_at if row is not None else None,
            disarmed_by=row.disarmed_by if row is not None else None,
            disarm_reason=row.disarm_reason if row is not None else None,
            last_audit=self._build_audit_summary(),
        )

    def get_readback_posture(
        self,
        *,
        scope: str = "auto_paper",
        trading_mode: str = "paper",
        now: datetime | None = None,
    ) -> TradingControlArmingReadbackPosture:
        evaluated_at = now or datetime.now(UTC)
        try:
            rows = self._load_rows(scope=scope, trading_mode=trading_mode)
        except Exception:
            return self._build_readback_posture(
                evaluated_at=evaluated_at,
                scope=scope,
                trading_mode=trading_mode,
                row=None,
                status="fail_closed",
                arming_state="disarmed",
                fail_closed_reason="durable_state_read_failed",
                durable_row_present=False,
                duplicate_rows_detected=False,
            )

        if len(rows) == 0:
            return self._build_readback_posture(
                evaluated_at=evaluated_at,
                scope=scope,
                trading_mode=trading_mode,
                row=None,
                status="fail_closed",
                arming_state="disarmed",
                fail_closed_reason="durable_state_missing",
                durable_row_present=False,
                duplicate_rows_detected=False,
            )

        if len(rows) > 1:
            return self._build_readback_posture(
                evaluated_at=evaluated_at,
                scope=scope,
                trading_mode=trading_mode,
                row=None,
                status="fail_closed",
                arming_state="disarmed",
                fail_closed_reason="durable_state_duplicate",
                durable_row_present=True,
                duplicate_rows_detected=True,
            )

        row = rows[0]
        if row.state not in _VALID_ARMING_STATES:
            return self._build_readback_posture(
                evaluated_at=evaluated_at,
                scope=scope,
                trading_mode=trading_mode,
                row=row,
                status="fail_closed",
                arming_state="disarmed",
                fail_closed_reason="durable_state_invalid",
                durable_row_present=True,
                duplicate_rows_detected=False,
            )

        if row.state == "armed":
            if row.armed_at is None or row.armed_by is None or row.expires_at is None:
                return self._build_readback_posture(
                    evaluated_at=evaluated_at,
                    scope=scope,
                    trading_mode=trading_mode,
                    row=row,
                    status="fail_closed",
                    arming_state="disarmed",
                    fail_closed_reason="durable_state_invalid",
                    durable_row_present=True,
                    duplicate_rows_detected=False,
                )
            if row.expires_at <= evaluated_at:
                return self._build_readback_posture(
                    evaluated_at=evaluated_at,
                    scope=scope,
                    trading_mode=trading_mode,
                    row=row,
                    status="fail_closed",
                    arming_state="disarmed",
                    fail_closed_reason="durable_state_expired",
                    durable_row_present=True,
                    duplicate_rows_detected=False,
                )
            return self._build_readback_posture(
                evaluated_at=evaluated_at,
                scope=scope,
                trading_mode=trading_mode,
                row=row,
                status="armed",
                arming_state="armed",
                fail_closed_reason=None,
                durable_row_present=True,
                duplicate_rows_detected=False,
            )

        return self._build_readback_posture(
            evaluated_at=evaluated_at,
            scope=scope,
            trading_mode=trading_mode,
            row=row,
            status="disarmed",
            arming_state="disarmed",
            fail_closed_reason=None,
            durable_row_present=True,
            duplicate_rows_detected=False,
        )

    def _get_or_create_row_for_write(self, *, scope: str, trading_mode: str) -> TradingControlArmingState:
        rows = self._load_rows(scope=scope, trading_mode=trading_mode)
        if len(rows) > 1:
            raise ValueError(f"Duplicate arming state rows detected for {scope}/{trading_mode}")
        if len(rows) == 1:
            return rows[0]

        row = TradingControlArmingState(
            scope=scope,
            trading_mode=trading_mode,
            state="disarmed",
        )
        self._session.add(row)
        return row

    def get_state(self, *, scope: str = "auto_paper", trading_mode: str = "paper") -> TradingControlArmingState | None:
        rows = self._load_rows(scope=scope, trading_mode=trading_mode)
        if len(rows) != 1:
            return None
        return rows[0]

    def get_effective_state(
        self,
        *,
        scope: str = "auto_paper",
        trading_mode: str = "paper",
        now: datetime | None = None,
    ) -> str:
        row = self.get_state(scope=scope, trading_mode=trading_mode)
        if row is None:
            return "disarmed"

        effective_now = now or datetime.now(UTC)
        if row.state not in _VALID_ARMING_STATES:
            return "disarmed"
        if row.state != "armed":
            return "disarmed"
        if row.armed_at is None or row.armed_by is None or row.expires_at is None:
            return "disarmed"
        if row.expires_at <= effective_now:
            return "disarmed"
        return "armed"

    def is_currently_armed(
        self,
        *,
        scope: str = "auto_paper",
        trading_mode: str = "paper",
        now: datetime | None = None,
    ) -> bool:
        return self.get_effective_state(scope=scope, trading_mode=trading_mode, now=now) == "armed"

    def arm_state(
        self,
        *,
        armed_by: str,
        expires_at: datetime,
        scope: str = "auto_paper",
        trading_mode: str = "paper",
        arm_reason: str | None = None,
        last_enablement_checked_at: datetime | None = None,
        last_enablement_status: str | None = None,
        last_enablement_blockers: list[str] | None = None,
        last_enablement_warnings: list[str] | None = None,
        client_request_id: str | None = None,
        metadata_json: dict[str, Any] | None = None,
        armed_at: datetime | None = None,
    ) -> TradingControlArmingState:
        if not armed_by:
            raise ValueError("armed_by is required")
        if last_enablement_status is not None and last_enablement_status not in _VALID_ENABLEMENT_STATUSES:
            raise ValueError(f"Unsupported enablement status: {last_enablement_status}")

        effective_armed_at = armed_at or datetime.now(UTC)
        if expires_at <= effective_armed_at:
            raise ValueError("expires_at must be later than armed_at")

        row = self._get_or_create_row_for_write(scope=scope, trading_mode=trading_mode)
        row.state = "armed"
        row.armed_at = effective_armed_at
        row.armed_by = armed_by
        row.arm_reason = arm_reason
        row.expires_at = expires_at
        row.last_enablement_checked_at = last_enablement_checked_at
        row.last_enablement_status = last_enablement_status
        row.last_enablement_blockers = list(last_enablement_blockers) if last_enablement_blockers is not None else None
        row.last_enablement_warnings = list(last_enablement_warnings) if last_enablement_warnings is not None else None
        row.client_request_id = client_request_id
        row.disarmed_at = None
        row.disarmed_by = None
        row.disarm_reason = None
        row.metadata_json = metadata_json

        self._session.commit()
        self._session.refresh(row)
        return row

    def disarm_state(
        self,
        *,
        disarmed_by: str,
        scope: str = "auto_paper",
        trading_mode: str = "paper",
        disarm_reason: str | None = None,
        metadata_json: dict[str, Any] | None = None,
        disarmed_at: datetime | None = None,
    ) -> TradingControlArmingState:
        if not disarmed_by:
            raise ValueError("disarmed_by is required")

        effective_disarmed_at = disarmed_at or datetime.now(UTC)
        row = self._get_or_create_row_for_write(scope=scope, trading_mode=trading_mode)
        row.state = "disarmed"
        row.expires_at = None
        row.disarmed_at = effective_disarmed_at
        row.disarmed_by = disarmed_by
        row.disarm_reason = disarm_reason
        row.metadata_json = metadata_json

        self._session.commit()
        self._session.refresh(row)
        return row