"""Create or purge visual seed dataset for UI preview workflows.

Usage (from apps/api):
  .venv/bin/python scripts/seed_visual_dataset.py --seed
  .venv/bin/python scripts/seed_visual_dataset.py --purge
  .venv/bin/python scripts/seed_visual_dataset.py --reset

The dataset is intentionally tagged and isolated for preview mode. By default,
production analytics and live history should exclude these rows.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.db.enums import (
    ApprovalStatus,
    AssetClass,
    CatalystType,
    HorizonLabel,
    OrderStatus,
    PositionStatus,
    RegimeType,
    SetupType,
    SignalStatus,
    TradeDirection,
)
from app.db.models.approval_request import ApprovalRequest
from app.db.models.asset import Asset
from app.db.models.audit_log import AuditLog
from app.db.models.model_version import ModelVersion
from app.db.models.paper_order import PaperOrder
from app.db.models.pnl_snapshot import PnlSnapshot
from app.db.models.position import Position
from app.db.models.risk_decision import RiskDecision
from app.db.models.signal import Signal
from app.db.models.signal_outcome import SignalOutcome
from app.db.session import SessionLocal
from app.services.execution_journal_service import ExecutionJournalService
from app.services.persistence_notification_service import PersistenceNotificationService
from app.services.visual_seed import VISUAL_SEED_PROVIDER, with_visual_seed_tags

RNG_SEED = 20260426
MANIFEST_PATH = Path(__file__).parent.parent / "app" / "data" / "visual_seed_manifest.json"


@dataclass
class SeedSummary:
    assets_seeded: int = 0
    signals_seeded: int = 0
    opportunities_seeded: int = 0
    risk_decisions_seeded: int = 0
    approvals_seeded: int = 0
    paper_orders_seeded: int = 0
    positions_seeded: int = 0
    signal_outcomes_seeded: int = 0
    pnl_snapshots_seeded: int = 0
    alert_rules_seeded: int = 0
    notifications_marked_read: int = 0
    journal_entries_seeded: int = 0


def _base_tags(seed_batch: str) -> dict[str, object]:
    return with_visual_seed_tags({"seed_batch": seed_batch})


def _price_base(symbol: str) -> float:
    table = {
        "AAPL": 191.20,
        "MSFT": 427.60,
        "NVDA": 942.10,
        "SPY": 514.70,
        "QQQ": 432.10,
        "GLD": 214.30,
        "EURUSD": 1.0824,
        "GBPUSD": 1.2671,
        "USDJPY": 154.12,
        "TSLA": 187.40,
        "AMD": 163.30,
    }
    return table.get(symbol, 100.0)


def purge_visual_seed(session) -> dict[str, int]:
    deleted: dict[str, int] = {}

    signal_ids = [
        row[0]
        for row in session.execute(
            select(Signal.id).where(Signal.provider_name == VISUAL_SEED_PROVIDER)
        ).all()
    ]

    def _del(model, name: str, where_clause) -> None:
        rows = session.query(model).filter(where_clause).all()
        deleted[name] = len(rows)
        for row in rows:
            session.delete(row)

    if signal_ids:
        _del(SignalOutcome, "signal_outcomes", SignalOutcome.signal_id.in_(signal_ids))
        _del(ApprovalRequest, "approval_requests", ApprovalRequest.signal_id.in_(signal_ids))
        _del(RiskDecision, "risk_decisions", RiskDecision.signal_id.in_(signal_ids))
        _del(PaperOrder, "paper_orders", PaperOrder.signal_id.in_(signal_ids))
        _del(Position, "positions", Position.signal_id.in_(signal_ids))
        _del(Signal, "signals", Signal.id.in_(signal_ids))
    else:
        deleted["signal_outcomes"] = 0
        deleted["approval_requests"] = 0
        deleted["risk_decisions"] = 0
        deleted["paper_orders"] = 0
        deleted["positions"] = 0
        deleted["signals"] = 0

    pnl_rows = session.query(PnlSnapshot).all()
    pnl_del = 0
    for row in pnl_rows:
        metadata = row.metadata_json or {}
        if isinstance(metadata, dict) and metadata.get("data_origin") == "visual_seed":
            session.delete(row)
            pnl_del += 1
    deleted["pnl_snapshots"] = pnl_del

    audit_rows = session.query(AuditLog).all()
    audit_del = 0
    for row in audit_rows:
        payload = row.payload_json or {}
        if isinstance(payload, dict) and payload.get("data_origin") == "visual_seed":
            session.delete(row)
            audit_del += 1
    deleted["audit_logs"] = audit_del

    assets = session.query(Asset).all()
    asset_del = 0
    for asset in assets:
        metadata = asset.metadata_json or {}
        if isinstance(metadata, dict) and metadata.get("data_origin") == "visual_seed":
            session.delete(asset)
            asset_del += 1
    deleted["assets"] = asset_del

    session.flush()

    journal_service = ExecutionJournalService()
    store = journal_service._read_store()  # noqa: SLF001 - intentional purge utility
    kept_store: dict[str, dict[str, object]] = {}
    removed_journals = 0
    for execution_id, payload in store.items():
        tags = payload.get("tags") if isinstance(payload, dict) else []
        if isinstance(tags, list) and "visual_seed" in [str(t).strip().lower() for t in tags]:
            removed_journals += 1
            continue
        kept_store[execution_id] = payload
    journal_service._write_store(kept_store)  # noqa: SLF001 - intentional purge utility
    deleted["execution_journals"] = removed_journals

    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()

    return deleted


def seed_visual_dataset(session) -> SeedSummary:
    rng = random.Random(RNG_SEED)
    summary = SeedSummary()
    seed_batch = f"visual_seed_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    tags = _base_tags(seed_batch)

    # 1) Assets: add a few demo-only symbols for richer visuals
    visual_assets = [
        {
            "symbol": "TSLA",
            "name": "Tesla, Inc.",
            "asset_class": AssetClass.EQUITY,
            "exchange": "NASDAQ",
            "sector": "Consumer Discretionary",
            "industry": "Auto Manufacturers",
        },
        {
            "symbol": "AMD",
            "name": "Advanced Micro Devices, Inc.",
            "asset_class": AssetClass.EQUITY,
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Semiconductors",
        },
    ]

    for row in visual_assets:
        existing = session.query(Asset).filter(Asset.symbol == row["symbol"]).one_or_none()
        if existing is None:
            asset = Asset(**row, metadata_json=tags)
            session.add(asset)
            summary.assets_seeded += 1

    session.flush()

    assets = (
        session.query(Asset)
        .filter(Asset.symbol.in_(["AAPL", "MSFT", "NVDA", "SPY", "QQQ", "GLD", "EURUSD", "GBPUSD", "USDJPY", "TSLA", "AMD"]))
        .all()
    )
    if not assets:
        raise RuntimeError("No assets available for visual seed dataset")
    asset_by_symbol = {a.symbol: a for a in assets}

    model = (
        session.query(ModelVersion)
        .order_by(ModelVersion.is_active.desc(), ModelVersion.created_at.desc())
        .first()
    )
    model_version_id = model.id if model is not None else None

    # 2) Signals + opportunities
    now = datetime.now(UTC)
    candidate_signals: list[Signal] = []
    execution_signals: list[Signal] = []

    setup_cycle = [
        SetupType.TREND_PULLBACK,
        SetupType.BREAKOUT_CONFIRMATION,
        SetupType.NEWS_CONTINUATION,
    ]
    regime_cycle = [RegimeType.TREND, RegimeType.RANGE, RegimeType.BREAKOUT, RegimeType.RISK_ON]
    catalyst_cycle = [CatalystType.MACRO, CatalystType.EARNINGS, CatalystType.SECTOR_NEWS, CatalystType.NONE]
    horizon_cycle = [HorizonLabel.INTRADAY, HorizonLabel.ONE_TO_THREE_DAYS, HorizonLabel.THREE_TO_TEN_DAYS]

    symbols = list(asset_by_symbol.keys())

    # 12 opportunity candidates
    for idx in range(12):
        symbol = symbols[idx % len(symbols)]
        asset = asset_by_symbol[symbol]
        base = _price_base(symbol)
        direction = TradeDirection.LONG if idx % 3 != 0 else TradeDirection.SHORT
        signal = Signal(
            id=uuid4(),
            asset_id=asset.id,
            model_version_id=model_version_id,
            provider_name=VISUAL_SEED_PROVIDER,
            scan_ts=now - timedelta(minutes=25 * idx + 5),
            timeframe=rng.choice(["15m", "1h", "4h"]),
            signal_status=SignalStatus.CANDIDATE,
            direction=direction,
            setup_type=setup_cycle[idx % len(setup_cycle)],
            regime=regime_cycle[idx % len(regime_cycle)],
            entry_min=round(base * (0.997 if direction == TradeDirection.LONG else 1.003), 6),
            entry_max=round(base * (1.001 if direction == TradeDirection.LONG else 1.007), 6),
            stop_price=round(base * (0.986 if direction == TradeDirection.LONG else 1.014), 6),
            target_price=round(base * (1.018 if direction == TradeDirection.LONG else 0.982), 6),
            confidence=round(rng.uniform(0.62, 0.91), 4),
            horizon_label=horizon_cycle[idx % len(horizon_cycle)],
            catalyst_type=catalyst_cycle[idx % len(catalyst_cycle)],
            catalyst_score=round(rng.uniform(0.32, 0.88), 4),
            catalyst_summary=f"{symbol} setup prepared for UI preview market context.",
            thesis=f"Demo thesis for {symbol}: continuation setup with controlled risk parameters.",
            invalidators_json=["Trend break", "Volatility spike"],
            signal_score=round(rng.uniform(58.0, 89.0), 4),
            raw_llm_json=with_visual_seed_tags({"seed_kind": "opportunity_candidate", "symbol": symbol, "seed_batch": seed_batch}),
        )
        session.add(signal)
        candidate_signals.append(signal)

    # 30 execution-linked signals
    execution_statuses = (
        [OrderStatus.CLOSED] * 14
        + [OrderStatus.FILLED] * 8
        + [OrderStatus.ACCEPTED] * 4
        + [OrderStatus.REJECTED] * 2
        + [OrderStatus.CANCELED] * 2
    )

    for idx, order_status in enumerate(execution_statuses):
        symbol = symbols[(idx + 3) % len(symbols)]
        asset = asset_by_symbol[symbol]
        base = _price_base(symbol) * (1 + rng.uniform(-0.02, 0.02))
        direction = TradeDirection.LONG if idx % 2 == 0 else TradeDirection.SHORT
        signal_status = (
            SignalStatus.CLOSED if order_status == OrderStatus.CLOSED
            else SignalStatus.PAPER_FILLED if order_status == OrderStatus.FILLED
            else SignalStatus.PAPER_SUBMITTED if order_status == OrderStatus.ACCEPTED
            else SignalStatus.RISK_BLOCKED
        )
        signal = Signal(
            id=uuid4(),
            asset_id=asset.id,
            model_version_id=model_version_id,
            provider_name=VISUAL_SEED_PROVIDER,
            scan_ts=now - timedelta(hours=rng.uniform(6, 72)),
            timeframe=rng.choice(["1h", "4h", "1d"]),
            signal_status=signal_status,
            direction=direction,
            setup_type=setup_cycle[idx % len(setup_cycle)],
            regime=regime_cycle[idx % len(regime_cycle)],
            entry_min=round(base * (0.998 if direction == TradeDirection.LONG else 1.002), 6),
            entry_max=round(base * (1.002 if direction == TradeDirection.LONG else 1.006), 6),
            stop_price=round(base * (0.989 if direction == TradeDirection.LONG else 1.011), 6),
            target_price=round(base * (1.016 if direction == TradeDirection.LONG else 0.984), 6),
            confidence=round(rng.uniform(0.51, 0.86), 4),
            horizon_label=horizon_cycle[idx % len(horizon_cycle)],
            catalyst_type=catalyst_cycle[idx % len(catalyst_cycle)],
            catalyst_score=round(rng.uniform(0.25, 0.84), 4),
            catalyst_summary=f"{symbol} execution scenario seeded for preview mode.",
            thesis=f"Seeded execution signal for {symbol} with realistic stop/target geometry.",
            invalidators_json=["Macro reversal", "Liquidity breakdown"],
            signal_score=round(rng.uniform(52.0, 86.0), 4),
            raw_llm_json=with_visual_seed_tags({"seed_kind": "execution_signal", "seed_batch": seed_batch}),
        )
        session.add(signal)
        execution_signals.append(signal)

    session.flush()
    summary.signals_seeded = len(candidate_signals) + len(execution_signals)
    summary.opportunities_seeded = len(candidate_signals)

    # 3) Risk decisions + approvals
    risk_target_signals = execution_signals[:22]
    for idx, signal in enumerate(risk_target_signals):
        approved = idx % 5 != 0
        decision = RiskDecision(
            id=uuid4(),
            signal_id=signal.id,
            approved="approved" if approved else "blocked",
            timestamp=signal.scan_ts + timedelta(minutes=3),
            blocking_rule=None if approved else "max_daily_drawdown",
            blocked_reasons_json=[] if approved else ["Daily drawdown threshold exceeded"],
            position_risk_pct=round(rng.uniform(0.35, 1.2), 4),
            notional_allowed=round(rng.uniform(4000, 24000), 4),
            correlation_bucket="tech" if idx % 2 == 0 else "macro",
            spread_ok=True,
            session_ok=True,
            drawdown_ok=approved,
            cooldown_ok=True,
            kill_switch_active=False,
            decision_json=with_visual_seed_tags({"seed_kind": "risk_decision", "seed_batch": seed_batch}),
        )
        session.add(decision)
        summary.risk_decisions_seeded += 1

    approval_target_signals = execution_signals[4:22]
    approval_statuses = (
        [ApprovalStatus.PENDING] * 6
        + [ApprovalStatus.APPROVED] * 6
        + [ApprovalStatus.REJECTED] * 4
        + [ApprovalStatus.EXPIRED] * 2
    )

    for idx, signal in enumerate(approval_target_signals[: len(approval_statuses)]):
        status = approval_statuses[idx]
        requested_at = signal.scan_ts + timedelta(minutes=4)
        expires_at = requested_at + timedelta(minutes=45)
        responded_at = None if status == ApprovalStatus.PENDING else requested_at + timedelta(minutes=10 + idx)
        approval = ApprovalRequest(
            id=uuid4(),
            signal_id=signal.id,
            status=status.value,
            requested_at=requested_at,
            expires_at=expires_at,
            responded_at=responded_at,
            approved_at=responded_at if status == ApprovalStatus.APPROVED else None,
            expired_at=responded_at if status == ApprovalStatus.EXPIRED else None,
            rejected_by="risk.engine@demo" if status == ApprovalStatus.REJECTED else None,
            approved_by="operator.demo@markethunter" if status == ApprovalStatus.APPROVED else None,
            notes=json.dumps(with_visual_seed_tags({"seed_kind": "approval", "seed_batch": seed_batch})),
        )
        session.add(approval)
        summary.approvals_seeded += 1

    # 4) Paper executions + positions
    order_rows: list[PaperOrder] = []
    for idx, signal in enumerate(execution_signals[: len(execution_statuses)]):
        symbol = next(sym for sym, asset in asset_by_symbol.items() if asset.id == signal.asset_id)
        fill_price = float((signal.entry_min + signal.entry_max) / 2)
        qty = round(rng.uniform(8, 140), 4)
        notional = round(fill_price * qty, 4)
        status = execution_statuses[idx]
        submitted_at = signal.scan_ts + timedelta(minutes=2)
        order = PaperOrder(
            id=uuid4(),
            signal_id=signal.id,
            asset_id=signal.asset_id,
            order_type="market",
            side="buy" if signal.direction == TradeDirection.LONG else "sell",
            direction=signal.direction.value,
            qty=qty,
            quantity=qty,
            filled_quantity=qty if status in {OrderStatus.FILLED, OrderStatus.CLOSED} else 0.0,
            notional=notional,
            stop_price=float(signal.stop_price or 0.0),
            status=status.value,
            timestamp=submitted_at,
            submitted_at=submitted_at,
            broker_order_id=-100000 - idx,
            commission=round(notional * 0.00035, 4),
            avg_fill_price=fill_price,
            ibkr_status="visual_seed_demo",
        )
        session.add(order)
        order_rows.append(order)

    summary.paper_orders_seeded = len(order_rows)
    session.flush()

    open_position_signals = [s for i, s in enumerate(execution_signals[: len(execution_statuses)]) if execution_statuses[i] in {OrderStatus.FILLED, OrderStatus.ACCEPTED}][:6]
    closed_position_signals = [s for i, s in enumerate(execution_signals[: len(execution_statuses)]) if execution_statuses[i] == OrderStatus.CLOSED][:4]

    for signal in open_position_signals:
        fill_price = float((signal.entry_min + signal.entry_max) / 2)
        current = fill_price * (1 + rng.uniform(-0.02, 0.03))
        qty = round(rng.uniform(10, 120), 4)
        side = "long" if signal.direction == TradeDirection.LONG else "short"
        unrealized = (current - fill_price) * qty if side == "long" else (fill_price - current) * qty
        session.add(
            Position(
                id=uuid4(),
                asset_id=signal.asset_id,
                signal_id=signal.id,
                status=PositionStatus.OPEN,
                side=side,
                avg_entry_price=fill_price,
                current_price=current,
                stop_price=float(signal.stop_price or 0.0),
                target_price=float(signal.target_price or 0.0),
                qty=qty,
                opened_at=signal.scan_ts + timedelta(minutes=8),
                unrealized_pnl=round(unrealized, 4),
                realized_pnl=0.0,
                broker_order_id=f"visual-seed-open-{signal.id}",
            )
        )
        summary.positions_seeded += 1

    for signal in closed_position_signals:
        fill_price = float((signal.entry_min + signal.entry_max) / 2)
        close_price = fill_price * (1 + rng.uniform(-0.025, 0.035))
        qty = round(rng.uniform(10, 90), 4)
        side = "long" if signal.direction == TradeDirection.LONG else "short"
        realized = (close_price - fill_price) * qty if side == "long" else (fill_price - close_price) * qty
        session.add(
            Position(
                id=uuid4(),
                asset_id=signal.asset_id,
                signal_id=signal.id,
                status=PositionStatus.CLOSED,
                side=side,
                avg_entry_price=fill_price,
                current_price=close_price,
                stop_price=float(signal.stop_price or 0.0),
                target_price=float(signal.target_price or 0.0),
                qty=qty,
                opened_at=signal.scan_ts + timedelta(minutes=9),
                closed_at=signal.scan_ts + timedelta(hours=7),
                close_reason="visual_seed_demo_exit",
                realized_pnl=round(realized, 4),
                unrealized_pnl=0.0,
                close_price=close_price,
                broker_order_id=f"visual-seed-closed-{signal.id}",
            )
        )
        summary.positions_seeded += 1

    # 5) Signal outcomes for realistic performance examples
    outcome_candidates = [s for i, s in enumerate(execution_signals[: len(execution_statuses)]) if execution_statuses[i] in {OrderStatus.CLOSED, OrderStatus.FILLED}]
    for idx, signal in enumerate(outcome_candidates[:26]):
        entry = float((signal.entry_min + signal.entry_max) / 2)
        is_win = idx % 4 != 0
        move_pct = rng.uniform(0.004, 0.028)
        if signal.direction == TradeDirection.LONG:
            exit_price = entry * (1 + move_pct if is_win else 1 - move_pct)
            pnl = move_pct if is_win else -move_pct
        else:
            exit_price = entry * (1 - move_pct if is_win else 1 + move_pct)
            pnl = move_pct if is_win else -move_pct

        session.add(
            SignalOutcome(
                id=uuid4(),
                signal_id=signal.id,
                asset_id=signal.asset_id,
                setup_type=signal.setup_type,
                direction=signal.direction,
                horizon_label=signal.horizon_label,
                catalyst_type=signal.catalyst_type,
                regime_at_entry=signal.regime,
                entry_price=entry,
                exit_price=round(exit_price, 6),
                predicted_direction_correct=is_win,
                actual_pnl_pct=round(pnl, 6),
                r_multiple=round((pnl / 0.01), 4),
                mae_pct=round(abs(pnl) * rng.uniform(0.2, 0.9), 6),
                mfe_pct=round(abs(pnl) * rng.uniform(1.0, 2.1), 6),
                closed_at=signal.scan_ts + timedelta(hours=rng.uniform(3, 40)),
            )
        )
        summary.signal_outcomes_seeded += 1

    # 6) Journal entries
    journal = ExecutionJournalService()
    for idx, order in enumerate(order_rows[:20]):
        tag = "worked" if idx % 3 == 0 else "partial" if idx % 3 == 1 else "stopped_out"
        journal.upsert_journal(
            order.id,
            outcome_tag=tag,
            note=f"Visual seed journal entry {idx + 1} for design preview.",
            tags=[
                "visual_seed",
                "demo",
                "exclude_from_reporting",
                "exclude_from_learning",
                "exclude_from_live_metrics",
            ],
        )
        summary.journal_entries_seeded += 1

    # 7) Alert rules and notification read state
    alert_rules = [
        ("AAPL", "status=filled"),
        ("MSFT", "status=blocked"),
        ("NVDA", "status=closed"),
        ("SPY", "status=accepted"),
    ]
    created_at = now - timedelta(hours=2)
    rule_ids: list[UUID] = []
    for idx, (asset, condition) in enumerate(alert_rules):
        rule_id = uuid4()
        rule_ids.append(rule_id)
        payload = with_visual_seed_tags(
            {
                "asset": asset,
                "condition": condition,
                "status": "active",
                "snoozed_until": None,
                "created_at": (created_at + timedelta(minutes=idx)).isoformat(),
                "updated_at": (created_at + timedelta(minutes=idx)).isoformat(),
                "seed_batch": seed_batch,
            }
        )
        session.add(
            AuditLog(
                entity_type="alert_rule",
                entity_id=rule_id,
                event_type="rule_created",
                payload_json=payload,
            )
        )
        summary.alert_rules_seeded += 1

    # 8) PnL snapshots
    base_equity = 250_000.0
    for idx in range(24):
        drift = rng.uniform(-1800, 2200)
        base_equity += drift
        open_pnl = rng.uniform(-4200, 5100)
        closed_pnl = rng.uniform(-18000, 24000)
        row = PnlSnapshot(
            id=uuid4(),
            snapshot_ts=now - timedelta(hours=24 - idx),
            equity=round(base_equity, 4),
            cash=round(base_equity * 0.42, 4),
            gross_exposure=round(rng.uniform(60_000, 180_000), 4),
            net_exposure=round(rng.uniform(-20_000, 120_000), 4),
            open_pnl=round(open_pnl, 4),
            closed_pnl=round(closed_pnl, 4),
            drawdown_pct=round(rng.uniform(0.4, 6.8), 4),
            win_rate_rolling=round(rng.uniform(0.44, 0.67), 4),
            profit_factor_rolling=round(rng.uniform(1.05, 1.9), 4),
            metadata_json=with_visual_seed_tags({"seed_kind": "pnl_snapshot", "seed_batch": seed_batch}),
        )
        session.add(row)
        summary.pnl_snapshots_seeded += 1

    session.flush()
    session.commit()

    # Derive notifications and mark a subset as read.
    notification_service = PersistenceNotificationService(session)
    notifications = notification_service.list_notifications(include_visual_seed=True)
    for row in notifications[:5]:
        notification_service.mark_as_read(row.notification_id, include_visual_seed=True)
        summary.notifications_marked_read += 1

    session.commit()

    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "provider_name": VISUAL_SEED_PROVIDER,
        "seed_batch": seed_batch,
        "tags": tags,
        "summary": asdict(summary),
        "reload_command": ".venv/bin/python scripts/seed_visual_dataset.py --reset",
        "purge_command": ".venv/bin/python scripts/seed_visual_dataset.py --purge",
        "notification_note": "Notification IDs are deterministic from alert IDs and execution IDs.",
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Market Hunter visual seed dataset")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--seed", action="store_true", help="Insert visual seed dataset")
    group.add_argument("--purge", action="store_true", help="Delete visual seed dataset")
    group.add_argument("--reset", action="store_true", help="Purge then seed visual dataset")
    args = parser.parse_args()

    session = SessionLocal()
    try:
        if args.purge:
            deleted = purge_visual_seed(session)
            session.commit()
            print("Purged visual seed data:")
            for key, count in sorted(deleted.items()):
                print(f"  {key}: {count}")
            return 0

        if args.reset:
            deleted = purge_visual_seed(session)
            session.commit()
            print("Reset step - purged existing visual seed rows:")
            for key, count in sorted(deleted.items()):
                print(f"  {key}: {count}")

        summary = seed_visual_dataset(session)
        print("Seeded visual dataset:")
        for key, value in asdict(summary).items():
            print(f"  {key}: {value}")
        print(f"Manifest: {MANIFEST_PATH}")
        return 0
    except Exception as exc:
        session.rollback()
        print(f"ERROR: {exc}")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
