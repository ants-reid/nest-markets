"""Route-level test for POST /workflow/run using mock signal mode.

Calls the async route handler directly via asyncio.run() — the same pattern
used by test_workflow_service.py — to avoid any anyio event loop state that
would block subsequent asyncio.run() calls in the same test session.

The fixture mirrors test_workflow_service.py exactly: both session AND
connection are explicitly closed before DROP SCHEMA so PostgreSQL does not
hold an open connection and hang teardown.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.workflow import run_workflow
from app.db.base import Base
from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.session import SessionLocal, engine
from app.schemas.workflow import (
    RiskContextRequest,
    SignalInputRequest,
    WorkflowRunRequest,
    WorkflowRunResponse,
)


@pytest.fixture()
def temp_db():
    """Yield a session scoped to a fresh temporary Postgres schema.

    Mirrors the test_workflow_service.py fixture exactly: both session AND
    connection are explicitly closed before DROP SCHEMA so PostgreSQL does
    not hold the schema open and hang the teardown.
    """
    schema_name = f"test_wroute_{uuid4().hex}"
    admin = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    admin.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    admin.close()

    connection = engine.connect()
    connection.execute(text(f'SET search_path TO "{schema_name}"'))
    connection.commit()
    Base.metadata.create_all(bind=connection)
    session = SessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()
        connection.close()  # must close before DROP SCHEMA or Postgres hangs
        admin = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        admin.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        admin.close()


def _seed_asset(session: Session, symbol: str = "EURUSD") -> None:
    asset = Asset(symbol=symbol, asset_class=AssetClass.FX, quote_currency="USD", is_active=True)
    session.add(asset)
    session.commit()


def test_workflow_run_blocked_path_with_mock_signal(temp_db: Session) -> None:
    """Route handler returns a blocked WorkflowRunResponse for mock low-confidence signal.

    The _MockSignalService always returns should_trade=False, confidence=0.0,
    signal_score=0.0 which guarantees the blocked execution path without any
    real LLM call.
    """
    _seed_asset(temp_db)

    request = WorkflowRunRequest(
        use_mock_signal=True,
        signal_input=SignalInputRequest(
            asset="EURUSD",
            timeframe="1h",
            latest_price=1.0815,
            feature_snapshot={"ema_fast": 101.2},
            catalyst_context={"headline": "CPI lower than expected"},
            risk_notes=None,
        ),
        risk_context=RiskContextRequest(
            spread_bps=10.0,
            daily_drawdown_pct=1.0,
            consecutive_losses=0,
            minutes_since_last_loss=None,
            correlated_exposure_count=0,
            market_quality_flag=True,
            account_equity=50000.0,
            requested_execution_mode="paper",
        ),
    )

    result: WorkflowRunResponse = asyncio.run(run_workflow(request, temp_db))

    # Mock signal always blocks: should_trade=False / confidence=0 / signal_score=0
    assert isinstance(result, WorkflowRunResponse)
    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert result.approval_request_id is None
    assert result.paper_execution_id is None
    assert result.live_execution_result is None
    assert isinstance(result.blocked_reasons, list)
    assert len(result.blocked_reasons) > 0
    assert result.signal_id is not None
