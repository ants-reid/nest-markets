from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.enums import PositionStatus
from app.db.session import get_db_session
from app.main import app


@pytest.fixture()
def client():
    mock_session = MagicMock()
    app.dependency_overrides[get_db_session] = lambda: (yield mock_session)
    try:
        with TestClient(app) as c:
            yield c, mock_session
    finally:
        app.dependency_overrides.pop(get_db_session, None)


def test_list_positions_returns_open_positions(client):
    c, session = client
    asset_id = uuid4()
    signal_id = uuid4()
    position_id = uuid4()
    row = SimpleNamespace(
        id=position_id,
        asset_id=asset_id,
        signal_id=signal_id,
        status=PositionStatus.OPEN,
        side="long",
        avg_entry_price=101.0,
        current_price=102.5,
        stop_price=99.0,
        target_price=110.0,
        qty=5.0,
        opened_at=datetime.now(UTC),
        closed_at=None,
        close_reason=None,
        realized_pnl=None,
        unrealized_pnl=7.5,
    )
    asset = SimpleNamespace(id=asset_id, symbol="AAPL")

    # Route was refactored to issue an inline SQLAlchemy select for open
    # positions (with a visual-seed-provider filter) instead of going through
    # PositionService.list_open_positions. The fixture must therefore stub
    # session.execute(...).scalars().all() rather than patching the service.
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [row]
    session.execute.return_value = execute_result

    def _get(model, object_id):
        if object_id == position_id:
            return row
        if object_id == asset_id:
            return asset
        return None
    session.get.side_effect = _get
    response = c.get("/execution/positions")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["asset_symbol"] == "AAPL"
    assert data[0]["status"] == "open"


def test_snapshot_position_pnl_records_snapshot(client):
    c, session = client
    position_id = uuid4()
    position_row = SimpleNamespace(id=position_id)
    snapshot_id = uuid4()
    snapshot_row = SimpleNamespace(
        id=snapshot_id,
        snapshot_ts=datetime.now(UTC),
        equity=12.5,
        cash=None,
        gross_exposure=None,
        net_exposure=None,
        open_pnl=12.5,
        closed_pnl=None,
        drawdown_pct=None,
        metadata_json={"position_id": str(position_id), "mark_price": 105.0},
    )

    def _get(model, object_id):
        if object_id == position_id:
            return position_row
        if object_id == snapshot_id:
            return snapshot_row
        return None

    session.get.side_effect = _get

    with patch("app.api.routes.execution.PositionService.mark_to_market", return_value=SimpleNamespace(
        unrealized_pnl=12.5,
        realized_pnl=None,
        side="long",
    )), patch("app.api.routes.execution.PnlService.record_snapshot", return_value=SimpleNamespace(id=snapshot_id)):
        response = c.post(f"/execution/positions/{position_id}/snapshot?mark_price=105")

    assert response.status_code == 200
    assert response.json()["metadata_json"]["position_id"] == str(position_id)


def test_fill_paper_order_opens_position(client):
    c, session = client
    execution_id = uuid4()
    signal_id = uuid4()
    asset_id = uuid4()
    row = SimpleNamespace(id=execution_id, signal_id=signal_id)
    signal = SimpleNamespace(id=signal_id, asset_id=asset_id, direction="long")
    filled = SimpleNamespace(
        execution_id=execution_id,
        status="filled",
        asset="AAPL",
        timeframe="1d",
        side="buy",
        qty=3.0,
        notional=300.0,
        stop_price=95.0,
        target_price=110.0,
        fill_price=100.0,
        reason=None,
    )

    session.get.side_effect = lambda model, object_id: signal if object_id == signal_id else None
    session.execute.return_value.scalars.return_value.first.return_value = None

    with patch("app.api.routes.execution.PersistencePaperExecutionService.get_paper_order", return_value=row), \
         patch("app.api.routes.execution.PersistencePaperExecutionService.build_service_result", return_value=filled), \
         patch("app.api.routes.execution.PersistencePaperExecutionService.persist_paper_execution"), \
         patch("app.api.routes.execution.PaperExecutionService.fill_order", return_value=filled), \
         patch("app.api.routes.execution.PositionService.open_position") as open_position:
        response = c.post(f"/execution/paper/{execution_id}/fill")

    assert response.status_code == 200
    open_position.assert_called_once()


def test_close_paper_order_closes_position(client):
    c, session = client
    execution_id = uuid4()
    signal_id = uuid4()
    position_id = uuid4()
    row = SimpleNamespace(id=execution_id, signal_id=signal_id)
    signal = SimpleNamespace(id=signal_id)
    position = SimpleNamespace(id=position_id)
    filled = SimpleNamespace(
        execution_id=execution_id,
        status="filled",
        asset="AAPL",
        timeframe="1d",
        side="buy",
        qty=3.0,
        notional=300.0,
        stop_price=95.0,
        target_price=110.0,
        fill_price=100.0,
        reason=None,
    )
    closed = SimpleNamespace(**{**filled.__dict__, "status": "closed", "fill_price": 104.0})

    session.get.side_effect = lambda model, object_id: signal if object_id == signal_id else None
    session.execute.return_value.scalars.return_value.first.return_value = position

    with patch("app.api.routes.execution.PersistencePaperExecutionService.get_paper_order", return_value=row), \
         patch("app.api.routes.execution.PersistencePaperExecutionService.build_service_result", return_value=filled), \
         patch("app.api.routes.execution.PersistencePaperExecutionService.persist_paper_execution"), \
         patch("app.api.routes.execution.PaperExecutionService.close_order", return_value=closed), \
         patch("app.api.routes.execution.PositionService.close_position") as close_position:
        response = c.post(f"/execution/paper/{execution_id}/close?close_price=104")

    assert response.status_code == 200
    close_position.assert_called_once_with(position_id, close_price=104.0, close_reason="paper_order_closed")
