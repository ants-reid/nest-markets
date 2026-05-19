"""QA-101 / QA-102 — PositionService and PnlService unit tests."""

from __future__ import annotations

from datetime import datetime, UTC
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.db.enums import PositionStatus
from app.db.models.pnl_snapshot import PnlSnapshot
from app.db.models.position import Position
from app.services.pnl_service import PnlService, PnlSnapshotInput
from app.services.position_service import OpenPositionInput, PositionService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_session() -> MagicMock:
    session = MagicMock(spec=Session)

    def _refresh(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()

    session.refresh.side_effect = _refresh
    return session


def _make_open_position_row(**overrides) -> Position:
    defaults = dict(
        id=uuid4(),
        asset_id=uuid4(),
        signal_id=None,
        status=PositionStatus.OPEN,
        side="long",
        avg_entry_price=1.0800,
        current_price=None,
        stop_price=1.0750,
        target_price=1.0900,
        qty=10000.0,
        opened_at=datetime.now(UTC),
        closed_at=None,
        close_reason=None,
        realized_pnl=None,
        unrealized_pnl=0.0,
    )
    defaults.update(overrides)
    row = Position(**{k: v for k, v in defaults.items() if hasattr(Position, k)})
    # Manually assign all fields since Position uses mapped_column
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


# ---------------------------------------------------------------------------
# QA-101: PositionService
# ---------------------------------------------------------------------------

class TestPositionService:
    """QA-101 — PositionService open, mark-to-market, close, list."""

    def test_open_position_creates_row_with_open_status(self):
        session = _make_mock_session()
        service = PositionService(session)
        inp = OpenPositionInput(
            asset_id=uuid4(),
            signal_id=uuid4(),
            side="long",
            avg_entry_price=1.0800,
            qty=10000.0,
            stop_price=1.0750,
            target_price=1.0900,
        )

        result = service.open_position(inp)

        session.add.assert_called_once()
        assert result.status == "open"
        assert result.side == "long"
        assert result.avg_entry_price == pytest.approx(1.0800)
        assert result.qty == pytest.approx(10000.0)

    def test_mark_to_market_updates_unrealized_pnl_long(self):
        session = _make_mock_session()
        row = _make_open_position_row(avg_entry_price=1.0800, qty=10000.0, side="long")
        session.get.return_value = row
        session.refresh.side_effect = lambda r: None
        service = PositionService(session)

        result = service.mark_to_market(row.id, current_price=1.0850)

        # (1.0850 - 1.0800) * 10000 = 50.0
        assert result.unrealized_pnl == pytest.approx(50.0)
        assert result.current_price == pytest.approx(1.0850)

    def test_mark_to_market_updates_unrealized_pnl_short(self):
        session = _make_mock_session()
        row = _make_open_position_row(avg_entry_price=1.0800, qty=10000.0, side="short")
        session.get.return_value = row
        session.refresh.side_effect = lambda r: None
        service = PositionService(session)

        result = service.mark_to_market(row.id, current_price=1.0750)

        # (1.0800 - 1.0750) * 10000 = 50.0
        assert result.unrealized_pnl == pytest.approx(50.0)

    def test_close_position_sets_closed_status_and_realized_pnl(self):
        session = _make_mock_session()
        row = _make_open_position_row(avg_entry_price=1.0800, qty=10000.0, side="long")
        session.get.return_value = row
        session.refresh.side_effect = lambda r: None
        service = PositionService(session)

        result = service.close_position(row.id, close_price=1.0900, close_reason="target_hit")

        assert result.status == "closed"
        assert result.realized_pnl == pytest.approx(100.0)  # (1.09 - 1.08) * 10000
        assert result.unrealized_pnl == pytest.approx(0.0)
        assert result.close_reason == "target_hit"
        assert result.closed_at is not None

    def test_close_position_raises_if_already_closed(self):
        session = _make_mock_session()
        row = _make_open_position_row(status=PositionStatus.CLOSED)
        session.get.return_value = row
        service = PositionService(session)

        with pytest.raises(ValueError, match="not open"):
            service.close_position(row.id, close_price=1.09)

    def test_close_position_raises_if_not_found(self):
        session = _make_mock_session()
        session.get.return_value = None
        service = PositionService(session)

        with pytest.raises(ValueError, match="not found"):
            service.close_position(uuid4(), close_price=1.09)

    def test_list_open_positions_returns_only_open(self):
        session = _make_mock_session()
        rows = [_make_open_position_row() for _ in range(3)]
        session.query.return_value.filter.return_value.all.return_value = rows
        service = PositionService(session)

        results = service.list_open_positions()
        assert len(results) == 3
        assert all(r.status == "open" for r in results)


# ---------------------------------------------------------------------------
# QA-102: PnlService
# ---------------------------------------------------------------------------

class TestPnlService:
    """QA-102 — PnlService record and retrieve snapshots."""

    def test_record_snapshot_creates_row(self):
        session = _make_mock_session()
        service = PnlService(session)
        inp = PnlSnapshotInput(equity=10500.0, cash=5000.0, open_pnl=500.0)

        result = service.record_snapshot(inp)

        session.add.assert_called_once()
        assert result.equity == pytest.approx(10500.0)
        assert result.cash == pytest.approx(5000.0)
        assert result.open_pnl == pytest.approx(500.0)

    def test_record_snapshot_uses_provided_timestamp(self):
        session = _make_mock_session()
        service = PnlService(session)
        ts = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)
        inp = PnlSnapshotInput(equity=10000.0, snapshot_ts=ts)

        result = service.record_snapshot(inp)
        assert result.snapshot_ts == ts

    def test_latest_snapshot_returns_none_when_empty(self):
        session = _make_mock_session()
        session.query.return_value.order_by.return_value.first.return_value = None
        service = PnlService(session)

        assert service.latest_snapshot() is None

    def test_latest_snapshot_returns_most_recent(self):
        session = _make_mock_session()
        ts = datetime.now(UTC)
        row = PnlSnapshot()
        row.id = uuid4()
        row.snapshot_ts = ts
        row.equity = 10500.0
        row.cash = row.gross_exposure = row.net_exposure = None
        row.open_pnl = row.closed_pnl = row.drawdown_pct = None
        row.win_rate_rolling = row.profit_factor_rolling = None
        row.metadata_json = None

        session.query.return_value.order_by.return_value.first.return_value = row
        service = PnlService(session)

        result = service.latest_snapshot()
        assert result is not None
        assert result.equity == pytest.approx(10500.0)

    def test_recent_snapshots_returns_oldest_first(self):
        session = _make_mock_session()
        rows = []
        for i in range(3):
            r = PnlSnapshot()
            r.id = uuid4()
            r.snapshot_ts = datetime(2026, 4, 24, i, 0, 0, tzinfo=UTC)
            r.equity = 10000.0 + i * 100
            r.cash = r.gross_exposure = r.net_exposure = None
            r.open_pnl = r.closed_pnl = r.drawdown_pct = None
            r.win_rate_rolling = r.profit_factor_rolling = None
            r.metadata_json = None
            rows.append(r)

        # query returns newest-first; service reverses for oldest-first
        session.query.return_value.order_by.return_value.limit.return_value.all.return_value = list(reversed(rows))
        service = PnlService(session)

        results = service.recent_snapshots(limit=3)
        assert len(results) == 3
        # First result should be earliest
        assert results[0].snapshot_ts < results[-1].snapshot_ts
