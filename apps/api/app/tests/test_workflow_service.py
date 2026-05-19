import asyncio
from uuid import uuid4
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.enums import ApprovalStatus, AssetClass, OrderStatus
from app.db.models.approval_request import ApprovalRequest as ApprovalRequestModel
from app.db.models.asset import Asset
from app.db.models.paper_order import PaperOrder
from app.db.models.risk_decision import RiskDecision as RiskDecisionModel
from app.db.models.signal import Signal as SignalModel
from app.db.session import SessionLocal, engine
from app.services.approval_service import ApprovalService
from app.services.execution_mode_service import ExecutionModeService
from app.services.live_execution_service import LiveExecutionService
from app.services.paper_execution_service import PaperExecutionService
from app.services.persistence_approval_service import PersistenceApprovalService
from app.services.persistence_paper_execution_service import PersistencePaperExecutionService
from app.services.persistence_signal_service import PersistenceSignalService
from app.services.risk_profile_service import RiskProfileService
from app.services.risk_service import RiskContext, RiskService
from app.services.signal_service import SignalInput, SignalOutput
from app.services.workflow_service import WorkflowService


class _FakeSignalService:
    def __init__(self, signal_output: SignalOutput) -> None:
        self._signal_output = signal_output

    async def generate_signal(self, signal_input: SignalInput) -> SignalOutput:
        _ = signal_input
        return self._signal_output


@pytest.fixture()
def db_session() -> Session:
    schema_name = f"test_workflow_{uuid4().hex}"
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
    session.commit()
    session.refresh(asset)
    return asset


def _signal_input() -> SignalInput:
    return SignalInput(
        feature_snapshot={"regime_preclassification": "trend", "ema_fast": 101.2},
        catalyst_context={"headline": "CPI lower than expected"},
        asset="EURUSD",
        timeframe="1h",
        latest_price=1.0815,
        risk_notes="No major event in next hour",
    )


def _signal_output(*, confidence: float = 0.75) -> SignalOutput:
    return SignalOutput(
        asset="EURUSD",
        timeframe="1h",
        direction="long",
        regime="trend",
        setup_type="trend_pullback",
        entry_zone=(1.0810, 1.0820),
        stop_price=1.0780,
        target_price=1.0880,
        confidence=confidence,
        horizon_label="1_3_days",
        catalyst_type="macro",
        catalyst_score=0.60,
        catalyst_summary="Macro backdrop remains supportive.",
        thesis="Price structure supports continuation from pullback.",
        invalidators=["1h close below 1.0780"],
        signal_score=76.0,
        should_trade=True,
    )


def _risk_context(mode: str) -> RiskContext:
    return RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode=mode,
    )


def _workflow_service(session: Session, signal_output: SignalOutput) -> WorkflowService:
    return WorkflowService(
        session=session,
        signal_service=_FakeSignalService(signal_output),
        risk_service=RiskService(
            profile=RiskProfileService().get_default_profile(),
            execution_mode_service=ExecutionModeService(),
        ),
        approval_service=ApprovalService(),
        paper_execution_service=PaperExecutionService(),
        live_execution_service=LiveExecutionService(),
        persistence_signal_service=PersistenceSignalService(session),
        persistence_approval_service=PersistenceApprovalService(session),
        persistence_paper_execution_service=PersistencePaperExecutionService(session),
    )


def test_blocked_workflow_stops_after_risk_and_persists_signal_and_risk_only(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output(confidence=0.20))

    result = asyncio.run(workflow.run(_signal_input(), _risk_context("paper")))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert result.approval_request_id is None
    assert result.paper_execution_id is None
    assert "confidence_below_threshold" in result.blocked_reasons
    assert result.live_execution_result is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_when_signal_score_below_threshold_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    low_signal_score_output = SignalOutput(**{**vars(_signal_output()), "signal_score": 40.0})
    workflow = _workflow_service(db_session, low_signal_score_output)

    result = asyncio.run(workflow.run(_signal_input(), _risk_context("paper")))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "signal_score_below_threshold" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_when_confidence_below_threshold_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    low_confidence_output = SignalOutput(**{**vars(_signal_output()), "confidence": 0.4})
    workflow = _workflow_service(db_session, low_confidence_output)

    result = asyncio.run(workflow.run(_signal_input(), _risk_context("paper")))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "confidence_below_threshold" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_when_direction_is_flat_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    flat_direction_output = SignalOutput(**{**vars(_signal_output()), "direction": "flat"})
    workflow = _workflow_service(db_session, flat_direction_output)

    result = asyncio.run(workflow.run(_signal_input(), _risk_context("paper")))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "signal_not_actionable" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_when_should_trade_is_false_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    no_trade_output = SignalOutput(**{**vars(_signal_output()), "should_trade": False})
    workflow = _workflow_service(db_session, no_trade_output)

    result = asyncio.run(workflow.run(_signal_input(), _risk_context("paper")))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "signal_not_actionable" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_with_multiple_reasons_when_should_trade_is_false_and_spread_above_cap(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    no_trade_output = SignalOutput(**{**vars(_signal_output()), "should_trade": False})
    workflow = _workflow_service(db_session, no_trade_output)

    blocked_context = RiskContext(
        spread_bps=40.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "signal_not_actionable" in result.blocked_reasons
    assert "spread_above_cap" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_paper_workflow_persists_signal_risk_and_paper_order(db_session: Session) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    result = asyncio.run(workflow.run(_signal_input(), _risk_context("paper")))

    assert result.risk_approved is True
    assert result.selected_execution_mode == "paper"
    assert result.paper_execution_id is not None
    assert result.approval_request_id is None
    assert result.live_execution_result is None

    signals = db_session.execute(select(SignalModel)).scalars().all()
    risk_rows = db_session.execute(select(RiskDecisionModel)).scalars().all()
    paper_orders = db_session.execute(select(PaperOrder)).scalars().all()

    assert len(signals) == 1
    assert len(risk_rows) == 1
    assert len(paper_orders) == 1
    assert paper_orders[0].id == result.paper_execution_id
    assert paper_orders[0].status == OrderStatus.ACCEPTED


def test_confirm_live_workflow_persists_signal_risk_and_approval_request(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    result = asyncio.run(workflow.run(_signal_input(), _risk_context("confirm_live")))

    assert result.risk_approved is True
    assert result.selected_execution_mode == "confirm_live"
    assert result.approval_request_id is not None
    assert result.paper_execution_id is None
    assert result.live_execution_result is None

    signals = db_session.execute(select(SignalModel)).scalars().all()
    risk_rows = db_session.execute(select(RiskDecisionModel)).scalars().all()
    approvals = db_session.execute(select(ApprovalRequestModel)).scalars().all()

    assert len(signals) == 1
    assert len(risk_rows) == 1
    assert len(approvals) == 1
    assert approvals[0].id == result.approval_request_id
    assert approvals[0].status == ApprovalStatus.PENDING


def test_auto_live_workflow_returns_disabled_live_result_and_persists_signal_and_risk_only(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    result = asyncio.run(workflow.run(_signal_input(), _risk_context("auto_live")))

    assert result.risk_approved is True
    assert result.selected_execution_mode == "auto_live"
    assert result.approval_request_id is None
    assert result.paper_execution_id is None
    assert result.live_execution_result is not None
    assert result.live_execution_result.accepted is False
    assert result.live_execution_result.status == "disabled"
    assert result.live_execution_result.reason == "live_execution_disabled_in_mvp"

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_build_live_request_sets_explicit_auto_live_execution_mode() -> None:
    workflow = WorkflowService(
        session=MagicMock(),
        signal_service=MagicMock(),
        risk_service=MagicMock(),
        approval_service=MagicMock(),
        paper_execution_service=MagicMock(),
        live_execution_service=MagicMock(),
        persistence_signal_service=MagicMock(),
        persistence_approval_service=MagicMock(),
        persistence_paper_execution_service=MagicMock(),
    )
    workflow._paper_execution_service.submit_order.return_value = MagicMock(
        side="buy",
        qty=2.5,
        notional=270.375,
    )

    request = workflow._build_live_request(
        _signal_output(),
        _signal_input(),
        allowed_risk_amount=100.0,
    )

    assert request.execution_mode == "auto_live"
    assert request.side == "buy"
    assert request.qty == 2.5


def test_workflow_blocks_when_kill_switch_is_active(db_session: Session) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=True,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "kill_switch_active" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_stays_blocked_for_confirm_live_when_risk_not_approved(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=True,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="confirm_live",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "kill_switch_active" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None
    assert result.live_execution_result is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_when_open_positions_cap_reached_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        open_positions_count=6,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "max_open_positions_exceeded" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_when_session_not_allowed_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=False,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "session_not_allowed" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_with_multiple_reasons_when_session_not_allowed_and_kill_switch_active(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=False,
        kill_switch_active=True,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "session_not_allowed" in result.blocked_reasons
    assert "kill_switch_active" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_when_spread_above_cap_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=40.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "spread_above_cap" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_when_daily_drawdown_exceeded_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=2.5,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "daily_drawdown_exceeded" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_when_cooldown_active_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=3,
        minutes_since_last_loss=60,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "cooldown_active" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_with_multiple_reasons_when_daily_drawdown_exceeded_and_cooldown_active(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=2.5,
        consecutive_losses=3,
        minutes_since_last_loss=60,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "daily_drawdown_exceeded" in result.blocked_reasons
    assert "cooldown_active" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_allows_when_cooldown_threshold_has_expired(db_session: Session) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    boundary_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=3,
        minutes_since_last_loss=180,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), boundary_context))

    assert result.risk_approved is True
    assert result.selected_execution_mode == "paper"
    assert "cooldown_active" not in result.blocked_reasons
    assert result.paper_execution_id is not None
    assert result.approval_request_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 1


def test_workflow_blocks_when_cooldown_active_with_null_minutes_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=3,
        minutes_since_last_loss=None,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "cooldown_active" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_allows_when_consecutive_losses_below_threshold_with_null_minutes(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    below_threshold_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=2,
        minutes_since_last_loss=None,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), below_threshold_context))

    assert result.risk_approved is True
    assert result.selected_execution_mode == "paper"
    assert "cooldown_active" not in result.blocked_reasons
    assert result.paper_execution_id is not None
    assert result.approval_request_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 1


def test_workflow_blocks_when_market_quality_flag_is_false_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=False,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "market_quality_bad" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_when_correlated_exposure_exceeded_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=2,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "correlated_exposure_exceeded" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_with_multiple_reasons_when_max_positions_exceeded_and_correlated_exposure_exceeded(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=2,
        open_positions_count=6,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "max_open_positions_exceeded" in result.blocked_reasons
    assert "correlated_exposure_exceeded" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_with_multiple_reasons_when_session_not_allowed_kill_switch_active_and_max_positions_exceeded(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        open_positions_count=6,
        session_allowed=False,
        kill_switch_active=True,
        market_quality_flag=True,
        account_equity=50000.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "session_not_allowed" in result.blocked_reasons
    assert "kill_switch_active" in result.blocked_reasons
    assert "max_open_positions_exceeded" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0


def test_workflow_blocks_when_account_equity_is_zero_and_persists_only_signal_and_risk(
    db_session: Session,
) -> None:
    _seed_asset(db_session)
    workflow = _workflow_service(db_session, _signal_output())

    blocked_context = RiskContext(
        spread_bps=10.0,
        daily_drawdown_pct=1.0,
        consecutive_losses=1,
        minutes_since_last_loss=240,
        correlated_exposure_count=1,
        open_positions_count=0,
        session_allowed=True,
        kill_switch_active=False,
        market_quality_flag=True,
        account_equity=0.0,
        requested_execution_mode="paper",
    )

    result = asyncio.run(workflow.run(_signal_input(), blocked_context))

    assert result.risk_approved is False
    assert result.selected_execution_mode == "blocked"
    assert "capital_or_risk_limit_block" in result.blocked_reasons
    assert result.approval_request_id is None
    assert result.paper_execution_id is None

    assert len(db_session.execute(select(SignalModel)).scalars().all()) == 1
    assert len(db_session.execute(select(RiskDecisionModel)).scalars().all()) == 1
    assert len(db_session.execute(select(ApprovalRequestModel)).scalars().all()) == 0
    assert len(db_session.execute(select(PaperOrder)).scalars().all()) == 0