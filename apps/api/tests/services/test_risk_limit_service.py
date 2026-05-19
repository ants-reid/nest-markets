"""Service tests for the MH-38 risk-limit foundation."""
from __future__ import annotations

from uuid import uuid4

from app.db.session import SessionLocal
from app.schemas.risk_limits import RiskLimitConfigCreateRequest, RiskLimitConfigUpdateRequest
from app.services.risk_limit_service import RiskLimitService


def _unique_scope(prefix: str) -> str:
    return f"{prefix[:10]}-{uuid4().hex[:8]}"


def test_create_and_list_risk_limit_config():
    session = SessionLocal()
    try:
        service = RiskLimitService(session)
        created = service.create_config(
            RiskLimitConfigCreateRequest(
                scope=_unique_scope("svc-create"),
                trading_mode="paper",
                max_order_notional=5000,
                max_total_exposure=25000,
            )
        )

        rows = service.list_configs()
        assert any(row.id == created.id for row in rows)
        assert float(created.max_order_notional) == 5000.0
    finally:
        session.close()


def test_update_risk_limit_config():
    session = SessionLocal()
    try:
        service = RiskLimitService(session)
        created = service.create_config(
            RiskLimitConfigCreateRequest(
                scope=_unique_scope("svc-update"),
                trading_mode="paper",
                max_order_notional=5000,
            )
        )

        updated = service.update_config(
            created.id,
            RiskLimitConfigUpdateRequest(max_total_exposure=30000),
        )

        assert updated is not None
        assert float(updated.max_total_exposure) == 30000.0
    finally:
        session.close()


def test_get_status_reports_missing_limits_when_not_configured():
    session = SessionLocal()
    try:
        service = RiskLimitService(session)
        service.create_config(
            RiskLimitConfigCreateRequest(
                scope=_unique_scope("svc-status"),
                trading_mode="live",
                max_order_notional=10000,
            )
        )

        status = service.get_status(trading_mode="live")
        assert status.enforcement_enabled is False
        assert status.has_max_order_notional is True
        assert status.has_max_total_exposure is False
        assert "max_total_exposure" in status.missing_limits
    finally:
        session.close()


def test_evaluate_order_against_limits_passes_when_under_limit():
    session = SessionLocal()
    try:
        service = RiskLimitService(session)
        service.create_config(
            RiskLimitConfigCreateRequest(
                scope=_unique_scope("svc-eval-pass"),
                trading_mode="paper",
                max_order_notional=10000,
            )
        )

        result = service.evaluate_order_against_limits(
            {
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 10,
                "estimated_price": 100,
                "estimated_notional": 1000,
                "trading_mode": "paper",
            }
        )

        assert result.allowed is True
        assert result.enforcement_enabled is False
        assert result.violations == []
    finally:
        session.close()


def test_evaluate_order_against_limits_returns_notional_violation():
    session = SessionLocal()
    try:
        service = RiskLimitService(session)
        service.create_config(
            RiskLimitConfigCreateRequest(
                scope=_unique_scope("svc-eval-notional"),
                trading_mode="paper",
                max_order_notional=500,
            )
        )

        result = service.evaluate_order_against_limits(
            {
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 10,
                "estimated_notional": 1000,
                "trading_mode": "paper",
            }
        )

        assert result.allowed is False
        assert any(v.code == "max_order_notional_exceeded" for v in result.violations)
    finally:
        session.close()


def test_evaluate_order_against_limits_returns_exposure_violation():
    session = SessionLocal()
    try:
        service = RiskLimitService(session)
        service.create_config(
            RiskLimitConfigCreateRequest(
                scope=_unique_scope("svc-eval-exposure"),
                trading_mode="paper",
                max_total_exposure=5000,
            )
        )

        result = service.evaluate_order_against_limits(
            {
                "ticker": "AAPL",
                "side": "BUY",
                "quantity": 10,
                "estimated_notional": 2000,
                "current_total_exposure": 4000,
                "trading_mode": "paper",
            }
        )

        assert result.allowed is False
        assert any(v.code == "max_total_exposure_exceeded" for v in result.violations)
    finally:
        session.close()