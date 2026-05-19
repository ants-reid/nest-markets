"""Service tests for the MH-39 trading halt foundation."""
from __future__ import annotations

from app.db.session import SessionLocal
from app.schemas.trading_halt import TradingHaltCreateRequest, TradingHaltResolveRequest
from app.services.trading_halt_service import TradingHaltService


def _create_halt(service: TradingHaltService, reason: str, scope: str = "global"):
    return service.create_halt(
        TradingHaltCreateRequest(
            halt_type="manual",
            scope=scope,
            trading_mode="paper",
            reason=reason,
            triggered_by="test-suite",
        )
    )


def test_status_is_clear_when_no_active_halt_exists():
    session = SessionLocal()
    try:
        service = TradingHaltService(session)
        status = service.get_status(scope="svc-clear-status")

        assert status.emergency_stop_active is False
        assert status.status == "clear"
        assert status.active_halt is None
        # MH-39 follow-up: halt enforcement was wired into broker preflight
        # and paper submit paths after this test was first written, so the
        # status payload now correctly reports enforcement_enabled=True.
        # This is a safety improvement, not a drift.
        assert status.enforcement_enabled is True
    finally:
        session.close()


def test_create_manual_halt_and_list_halts():
    session = SessionLocal()
    try:
        service = TradingHaltService(session)
        created = _create_halt(service, "manual operator stop", scope="svc-list-halts")

        listing = service.list_halts(status="active")

        assert any(item.id == created.id for item in listing.items)
        assert created.status == "active"
        assert created.reason == "manual operator stop"
    finally:
        session.close()


def test_status_shows_active_halt_and_blocked_reason():
    session = SessionLocal()
    try:
        service = TradingHaltService(session)
        created = _create_halt(service, "risk alarm triggered", scope="svc-active-status")

        status = service.get_status(scope="svc-active-status")

        assert status.emergency_stop_active is True
        assert status.status == "active"
        assert status.active_halt is not None
        assert status.active_halt.id == created.id
        assert "risk alarm triggered" in (status.blocked_reason or "")
        # MH-39 follow-up: enforcement is now actively wired (see
        # test_status_is_clear_when_no_active_halt_exists for context).
        assert status.enforcement_enabled is True
    finally:
        session.close()


def test_resolve_halt_and_status_returns_clear_after_resolve():
    session = SessionLocal()
    try:
        service = TradingHaltService(session)
        created = _create_halt(service, "system maintenance", scope="svc-resolve")

        resolved = service.resolve_halt(
            created.id,
            TradingHaltResolveRequest(resolved_by="ops", resolution_notes="cleared after maintenance"),
        )
        status = service.get_status(scope="svc-resolve")

        assert resolved is not None
        assert resolved.status == "resolved"
        assert resolved.resolved_by == "ops"
        assert resolved.resolution_notes == "cleared after maintenance"
        assert status.emergency_stop_active is False
        assert status.status == "clear"
    finally:
        session.close()


def test_cannot_resolve_unknown_halt():
    session = SessionLocal()
    try:
        service = TradingHaltService(session)
        resolved = service.resolve_halt(
            "00000000-0000-0000-0000-000000000000",
            TradingHaltResolveRequest(resolved_by="ops"),
        )

        assert resolved is None
    finally:
        session.close()


def test_multiple_active_halts_choose_latest_active():
    session = SessionLocal()
    try:
        service = TradingHaltService(session)
        first = _create_halt(service, "first halt", scope="svc-multi-active")
        latest = _create_halt(service, "latest halt", scope="svc-multi-active")

        active = service.get_active_halt(scope="svc-multi-active")

        assert active is not None
        assert active.id in {first.id, latest.id}
        assert active.id == latest.id
    finally:
        session.close()