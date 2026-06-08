"""Focused route tests for persisted alert rules and active alerts lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.enums import AssetClass, OrderStatus, SetupType, SignalStatus, TradeDirection
from app.db.models.asset import Asset
from app.db.models.paper_order import PaperOrder
from app.db.models.signal import Signal
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app


def _seed_asset_signal_order(session: Session, *, symbol: str = "EURUSD", status: OrderStatus = OrderStatus.ACCEPTED) -> None:
    asset = Asset(symbol=symbol, asset_class=AssetClass.FX, quote_currency="USD", is_active=True)
    session.add(asset)
    session.flush()

    signal = Signal(
        asset_id=asset.id,
        scan_ts=datetime.now(UTC),
        timeframe="1h",
        signal_status=SignalStatus.PAPER_SUBMITTED,
        direction=TradeDirection.LONG,
        setup_type=SetupType.TREND_PULLBACK,
    )
    session.add(signal)
    session.flush()

    order = PaperOrder(
        signal_id=signal.id,
        order_type="market",
        side="buy",
        qty=100,
        notional=108.15,
        stop_price=1.079,
        status=status,
    )
    session.add(order)
    session.commit()


def _db_session() -> tuple[Session, str, Connection]:
    schema_name = f"test_alert_routes_{uuid4().hex}"

    try:
        admin_connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    except ProgrammingError:
        engine.dispose()
        admin_connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    admin_connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    admin_connection.close()

    connection = engine.connect()
    connection.execute(text(f'SET search_path TO "{schema_name}"'))
    connection.commit()
    Base.metadata.create_all(bind=connection)

    return SessionLocal(bind=connection), schema_name, connection


def _cleanup_schema(schema_name: str) -> None:
    """Drop one temporary test schema."""
    try:
        admin_connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    except ProgrammingError:
        engine.dispose()
        admin_connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    admin_connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
    admin_connection.close()


def test_alert_rule_create_and_list() -> None:
    db_session, schema_name, connection = _db_session()

    def _override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_db_session
    try:
        with TestClient(app) as client:
            create_response = client.post(
                "/approvals/alerts/rules",
                json={"asset": "EURUSD", "condition": "status = submitted"},
            )
            assert create_response.status_code == 200
            payload = create_response.json()
            assert payload["asset"] == "EURUSD"
            assert payload["condition"] == "status = submitted"
            assert payload["status"] == "active"

            list_response = client.get("/approvals/alerts/rules")
            assert list_response.status_code == 200
            listed = list_response.json()
            assert len(listed) == 1
            assert listed[0]["rule_id"] == payload["rule_id"]
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        db_session.close()
        connection.close()
        _cleanup_schema(schema_name)


def test_alert_rule_acknowledge_and_snooze() -> None:
    db_session, schema_name, connection = _db_session()

    def _override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_db_session
    try:
        with TestClient(app) as client:
            create_response = client.post(
                "/approvals/alerts/rules",
                json={"asset": "EURUSD", "condition": "status = submitted"},
            )
            assert create_response.status_code == 200
            rule_id = create_response.json()["rule_id"]

            acknowledge_response = client.post(f"/approvals/alerts/rules/{rule_id}/acknowledge")
            assert acknowledge_response.status_code == 200
            assert acknowledge_response.json()["status"] == "acknowledged"

            snooze_response = client.post(f"/approvals/alerts/rules/{rule_id}/snooze", json={"minutes": 30})
            assert snooze_response.status_code == 200
            snoozed_payload = snooze_response.json()
            assert snoozed_payload["status"] == "snoozed"
            assert snoozed_payload["snoozed_until"] is not None
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        db_session.close()
        connection.close()
        _cleanup_schema(schema_name)


def test_active_alerts_list_from_persisted_rule_and_execution() -> None:
    db_session, schema_name, connection = _db_session()
    _seed_asset_signal_order(db_session, status=OrderStatus.ACCEPTED)

    def _override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_db_session
    try:
        with TestClient(app) as client:
            create_response = client.post(
                "/approvals/alerts/rules",
                json={"asset": "EURUSD", "condition": "status = submitted"},
            )
            assert create_response.status_code == 200

            active_response = client.get("/approvals/alerts/active")
            assert active_response.status_code == 200
            alerts = active_response.json()
            assert len(alerts) == 1
            assert alerts[0]["asset"] == "EURUSD"
            assert alerts[0]["status"] == "submitted"
            assert alerts[0]["rule_id"] == create_response.json()["rule_id"]
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        db_session.close()
        connection.close()
        _cleanup_schema(schema_name)


def test_alert_notifications_list_and_mark_read() -> None:
    db_session, schema_name, connection = _db_session()
    _seed_asset_signal_order(db_session, status=OrderStatus.ACCEPTED)

    def _override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_db_session
    try:
        with TestClient(app) as client:
            create_response = client.post(
                "/approvals/alerts/rules",
                json={"asset": "EURUSD", "condition": "status = submitted"},
            )
            assert create_response.status_code == 200

            list_response = client.get("/approvals/alerts/notifications")
            assert list_response.status_code == 200
            notifications = list_response.json()
            assert len(notifications) == 1
            assert notifications[0]["asset"] == "EURUSD"
            assert notifications[0]["is_read"] is False

            notification_id = notifications[0]["notification_id"]
            expected = str(
                uuid5(
                    NAMESPACE_URL,
                    f"market-hunter-alert-notification:{notifications[0]['alert_id']}",
                )
            )
            assert notification_id == expected

            read_response = client.post(f"/approvals/alerts/notifications/{notification_id}/read")
            assert read_response.status_code == 200
            read_payload = read_response.json()
            assert read_payload["is_read"] is True
            assert read_payload["read_at"] is not None

            list_after_response = client.get("/approvals/alerts/notifications")
            assert list_after_response.status_code == 200
            notifications_after = list_after_response.json()
            assert notifications_after[0]["is_read"] is True

            missing_response = client.post(
                "/approvals/alerts/notifications/11111111-1111-1111-1111-111111111111/read"
            )
            assert missing_response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        db_session.close()
        connection.close()
        _cleanup_schema(schema_name)
