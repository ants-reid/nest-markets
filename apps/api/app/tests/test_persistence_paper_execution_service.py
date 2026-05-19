import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from uuid import uuid4

from app.db.base import Base
from app.db.enums import AssetClass, OrderStatus
from app.db.models.asset import Asset
from app.db.models.paper_order import PaperOrder
from app.db.session import SessionLocal, engine
from app.services.paper_execution_service import PaperExecutionService
from app.services.persistence_paper_execution_service import PersistencePaperExecutionService
from app.services.persistence_signal_service import PersistenceSignalService
from app.services.signal_service import SignalOutput


@pytest.fixture()
def db_session() -> Session:
    schema_name = f"test_persistence_paper_{uuid4().hex}"
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


def test_persist_paper_execution_creates_accepted_order_row(db_session: Session) -> None:
    _seed_asset(db_session)
    signal_row = PersistenceSignalService(db_session).persist_signal(_signal())
    execution_service = PaperExecutionService()
    persistence_service = PersistencePaperExecutionService(db_session)

    submitted = execution_service.submit_order(
        signal=_signal(),
        allowed_risk_amount=100.0,
        latest_price=1.0815,
    )

    row = persistence_service.persist_paper_execution(signal_row.id, submitted)
    fetched = db_session.execute(select(PaperOrder).where(PaperOrder.id == row.id)).scalar_one()

    assert fetched.signal_id == signal_row.id
    assert fetched.order_type == "market"
    assert fetched.side == "buy"
    assert float(fetched.qty) > 0.0
    assert float(fetched.notional) > 0.0
    assert fetched.status == OrderStatus.ACCEPTED


def test_persist_paper_execution_updates_blocked_status_to_rejected(db_session: Session) -> None:
    _seed_asset(db_session)
    signal_row = PersistenceSignalService(db_session).persist_signal(_signal())
    execution_service = PaperExecutionService()
    persistence_service = PersistencePaperExecutionService(db_session)

    blocked_signal = SignalOutput(**{**_signal().__dict__, "stop_price": 1.0825})
    blocked = execution_service.submit_order(
        signal=blocked_signal,
        allowed_risk_amount=100.0,
        latest_price=1.0815,
    )

    row = persistence_service.persist_paper_execution(signal_row.id, blocked)
    fetched = db_session.execute(select(PaperOrder).where(PaperOrder.id == row.id)).scalar_one()

    assert fetched.signal_id == signal_row.id
    assert fetched.status == OrderStatus.REJECTED
    assert float(fetched.qty) == 0.0
    assert float(fetched.notional) == 0.0