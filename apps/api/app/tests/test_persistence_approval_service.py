from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.enums import ApprovalStatus, AssetClass
from app.db.models.approval_request import ApprovalRequest as ApprovalRequestModel
from app.db.models.asset import Asset
from app.db.session import SessionLocal, engine
from app.services.approval_service import ApprovalService
from app.services.persistence_approval_service import PersistenceApprovalService
from app.services.persistence_signal_service import PersistenceSignalService
from app.services.signal_service import SignalOutput


@pytest.fixture()
def db_session() -> Session:
    schema_name = f"test_persistence_approval_{uuid4().hex}"
    admin_connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    admin_connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    admin_connection.close()

    connection = engine.connect()
    connection.execute(text(f'SET search_path TO "{schema_name}"'))
    connection.commit()
    Base.metadata.create_all(bind=connection)
    session = SessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()
        connection.close()
        admin_connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        admin_connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        admin_connection.close()


def _seed_asset(session: Session, symbol: str = "EURUSD") -> Asset:
    asset = Asset(symbol=symbol, asset_class=AssetClass.FX, quote_currency="USD", is_active=True)
    session.add(asset)
    session.flush()
    session.refresh(asset)
    return asset


def _signal(symbol: str = "EURUSD") -> SignalOutput:
    return SignalOutput(
        asset=symbol,
        timeframe="1h",
        direction="long",
        regime="trend",
        setup_type="trend_pullback",
        entry_zone=(1.081, 1.082),
        stop_price=1.078,
        target_price=1.088,
        confidence=0.74,
        horizon_label="1_3_days",
        catalyst_type="macro",
        catalyst_score=0.6,
        catalyst_summary="Macro context supportive",
        thesis="Trend continuation",
        invalidators=["Break below 1.078"],
        signal_score=75.0,
        should_trade=True,
    )


def test_persist_approval_request_creates_pending_row(db_session: Session) -> None:
    _seed_asset(db_session)
    signal_row = PersistenceSignalService(db_session).persist_signal(_signal())
    approval_service = ApprovalService()
    persistence_service = PersistenceApprovalService(db_session)
    now = datetime(2026, 4, 22, 12, 0, tzinfo=UTC)

    request = approval_service.create_request(
        signal=_signal(),
        execution_mode="confirm_live",
        risk_approved=True,
        ttl_minutes=30,
        now=now,
    )

    row = persistence_service.persist_approval_request(signal_row.id, request)
    fetched = db_session.execute(
        select(ApprovalRequestModel).where(ApprovalRequestModel.id == row.id)
    ).scalar_one()

    assert fetched.signal_id == signal_row.id
    assert fetched.status == ApprovalStatus.PENDING
    assert fetched.requested_at == now
    assert fetched.expires_at == now + timedelta(minutes=30)


def test_persist_approval_request_updates_expired_status(db_session: Session) -> None:
    _seed_asset(db_session)
    signal_row = PersistenceSignalService(db_session).persist_signal(_signal())
    approval_service = ApprovalService()
    persistence_service = PersistenceApprovalService(db_session)
    now = datetime(2026, 4, 22, 12, 0, tzinfo=UTC)

    pending_request = approval_service.create_request(
        signal=_signal(),
        execution_mode="confirm_live",
        risk_approved=True,
        ttl_minutes=1,
        now=now,
    )
    persistence_service.persist_approval_request(signal_row.id, pending_request)

    expired_request = replace(pending_request, status="expired")
    row = persistence_service.persist_approval_request(signal_row.id, expired_request)

    fetched = db_session.execute(
        select(ApprovalRequestModel).where(ApprovalRequestModel.id == row.id)
    ).scalar_one()

    assert fetched.id == pending_request.request_id
    assert fetched.status == ApprovalStatus.EXPIRED
