from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.enums import AssetClass, SignalStatus
from app.db.models.asset import Asset
from app.db.models.risk_decision import RiskDecision as RiskDecisionModel
from app.db.models.signal import Signal as SignalModel
from app.db.session import SessionLocal, engine
from app.services.persistence_signal_service import PersistenceSignalService
from app.services.risk_service import RiskDecision
from app.services.signal_service import SignalOutput


@pytest.fixture()
def db_session() -> Session:
    schema_name = f"test_persistence_signal_{uuid4().hex}"
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
        catalyst_score=0.63,
        catalyst_summary="Macro backdrop supportive",
        thesis="Trend continuation above reclaimed structure",
        invalidators=["Break below 1.078"],
        signal_score=76.0,
        should_trade=True,
    )


def test_persist_signal_creates_row_with_expected_mapped_fields(db_session: Session) -> None:
    _seed_asset(db_session)
    service = PersistenceSignalService(db_session)
    scan_ts = datetime(2026, 4, 22, tzinfo=UTC)

    persisted = service.persist_signal(
        _signal(),
        scan_ts=scan_ts,
        provider_name="mock-provider",
        raw_llm_json={"source": "test"},
        signal_status=SignalStatus.CANDIDATE,
    )

    row = db_session.execute(select(SignalModel).where(SignalModel.id == persisted.id)).scalar_one()

    assert row.timeframe == "1h"
    assert row.provider_name == "mock-provider"
    assert row.signal_status == SignalStatus.CANDIDATE
    assert row.direction.value == "long"
    assert row.setup_type.value == "trend_pullback"
    assert row.regime.value == "trend"
    assert float(row.entry_min) == 1.081
    assert float(row.entry_max) == 1.082
    assert float(row.signal_score) == 76.0
    assert row.invalidators_json == ["Break below 1.078"]
    assert row.raw_llm_json == {"source": "test"}
    assert row.scan_ts == scan_ts


def test_persist_risk_decision_creates_blocked_row_with_audit_payload(db_session: Session) -> None:
    _seed_asset(db_session)
    signal_service = PersistenceSignalService(db_session)
    persisted_signal = signal_service.persist_signal(_signal())

    decision = RiskDecision(
        approved=False,
        blocked_reasons=["confidence_below_threshold", "market_quality_bad"],
        allowed_risk_amount=0.0,
        selected_execution_mode="blocked",
    )

    row = signal_service.persist_risk_decision(persisted_signal.id, decision)
    fetched = db_session.execute(
        select(RiskDecisionModel).where(RiskDecisionModel.id == row.id)
    ).scalar_one()

    assert fetched.signal_id == persisted_signal.id
    assert fetched.approved is False
    assert fetched.blocked_reasons_json == ["confidence_below_threshold", "market_quality_bad"]
    assert float(fetched.notional_allowed or Decimal("0")) == 0.0
    assert fetched.decision_json == {
        "approved": False,
        "blocked_reasons": ["confidence_below_threshold", "market_quality_bad"],
        "allowed_risk_amount": 0.0,
        "selected_execution_mode": "blocked",
    }
