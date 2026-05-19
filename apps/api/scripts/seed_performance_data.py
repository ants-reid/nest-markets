"""Seed script: insert realistic multi-asset signal outcomes for performance page.

Run from apps/api/:
    .venv/bin/python scripts/seed_performance_data.py
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

# ── bring app modules in scope ───────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.session import get_db_session
from app.db.models.asset import Asset
from app.db.models.signal import Signal
from app.db.models.signal_outcome import SignalOutcome
from app.db.enums import (
    AssetClass, CatalystType, HorizonLabel, RegimeType,
    SetupType, SignalStatus, TradeDirection,
)

SEED = 42
random.seed(SEED)

# ── asset definitions ─────────────────────────────────────────────────────────
NEW_ASSETS = [
    dict(symbol="AAPL",   name="Apple Inc.",               asset_class=AssetClass.EQUITY),
    dict(symbol="SPY",    name="SPDR S&P 500 ETF",          asset_class=AssetClass.ETF),
    dict(symbol="QQQ",    name="Invesco QQQ Trust",          asset_class=AssetClass.ETF),
    dict(symbol="GBPUSD", name="British Pound / US Dollar",  asset_class=AssetClass.FX),
    dict(symbol="USDJPY", name="US Dollar / Japanese Yen",   asset_class=AssetClass.FX),
    dict(symbol="NVDA",   name="NVIDIA Corporation",         asset_class=AssetClass.EQUITY),
    dict(symbol="MSFT",   name="Microsoft Corporation",      asset_class=AssetClass.EQUITY),
    dict(symbol="GLD",    name="SPDR Gold Shares",           asset_class=AssetClass.COMMODITY_PROXY),
]

SETUPS    = [s for s in SetupType if s != SetupType.NONE]
REGIMES   = [r for r in RegimeType]
CATALYSTS = [c for c in CatalystType]
HORIZONS  = [h for h in HorizonLabel]
DIRECTIONS = [TradeDirection.LONG, TradeDirection.SHORT]

# Win-rate biases per setup (so charts look interesting, not random 50%)
SETUP_WIN_BIAS = {
    SetupType.TREND_PULLBACK:         0.65,
    SetupType.BREAKOUT_CONFIRMATION:  0.58,
    SetupType.NEWS_CONTINUATION:      0.45,
}

# Per-asset win-rate multiplier (slight edge on indices)
ASSET_WIN_BIAS: dict[str, float] = {
    "SPY": 0.70, "QQQ": 0.68, "NVDA": 0.62, "AAPL": 0.60,
    "MSFT": 0.60, "GBPUSD": 0.50, "USDJPY": 0.50,
    "EURUSD": 0.52, "GLD": 0.55,
}

def _rand_ts(days_ago_max: int = 180) -> datetime:
    offset = random.randint(0, days_ago_max * 24 * 3600)
    return datetime.now(timezone.utc) - timedelta(seconds=offset)


def _make_signal(asset_id: uuid.UUID, setup: SetupType, direction: TradeDirection,
                 regime: RegimeType, catalyst: CatalystType, horizon: HorizonLabel,
                 ts: datetime) -> Signal:
    entry = round(random.uniform(10, 500), 4)
    move  = entry * random.uniform(0.005, 0.03)
    stop  = entry - move if direction == TradeDirection.LONG else entry + move
    tgt   = entry + move * 2 if direction == TradeDirection.LONG else entry - move * 2
    return Signal(
        id=uuid.uuid4(),
        asset_id=asset_id,
        scan_ts=ts,
        timeframe="1d",
        signal_status=SignalStatus.CLOSED,
        direction=direction,
        setup_type=setup,
        regime=regime,
        catalyst_type=catalyst,
        horizon_label=horizon,
        entry_min=entry - 0.001,
        entry_max=entry + 0.001,
        stop_price=stop,
        target_price=tgt,
        confidence=round(random.uniform(0.45, 0.95), 4),
    )


def _make_outcome(signal: Signal, asset_id: uuid.UUID, win: bool) -> SignalOutcome:
    entry = float(signal.entry_min or 100)
    move  = entry * random.uniform(0.005, 0.025)
    if win:
        exit_p = entry + move if signal.direction == TradeDirection.LONG else entry - move
        pnl    = round(move / entry, 6)
        r_mult = round(random.uniform(1.0, 3.5), 4)
    else:
        exit_p = entry - move if signal.direction == TradeDirection.LONG else entry + move
        pnl    = round(-move / entry, 6)
        r_mult = round(random.uniform(-1.5, -0.1), 4)

    return SignalOutcome(
        id=uuid.uuid4(),
        signal_id=signal.id,
        asset_id=asset_id,
        setup_type=signal.setup_type,
        direction=signal.direction,
        horizon_label=signal.horizon_label,
        catalyst_type=signal.catalyst_type,
        regime_at_entry=signal.regime,
        entry_price=entry,
        exit_price=round(exit_p, 4),
        predicted_direction_correct=win,
        actual_pnl_pct=pnl,
        r_multiple=r_mult,
        mae_pct=round(abs(pnl) * random.uniform(0.3, 1.0), 6),
        mfe_pct=round(abs(pnl) * random.uniform(1.0, 2.5), 6),
        closed_at=signal.scan_ts + timedelta(days=random.randint(1, 5)),
    )


def run() -> None:
    db = next(get_db_session())

    # ── upsert assets ─────────────────────────────────────────────────────────
    symbol_to_id: dict[str, uuid.UUID] = {}

    # seed existing EURUSD id
    existing = db.query(Asset).all()
    for a in existing:
        symbol_to_id[a.symbol] = a.id

    for defn in NEW_ASSETS:
        sym = defn["symbol"]
        if sym not in symbol_to_id:
            asset = Asset(id=uuid.uuid4(), **defn)
            db.add(asset)
            symbol_to_id[sym] = asset.id
            print(f"  + asset {sym}")
        else:
            print(f"  = asset {sym} already exists")

    db.flush()

    # ── generate signals + outcomes ───────────────────────────────────────────
    # ~20 outcomes per asset → ~180 total (well above min_samples=10)
    signals_added = 0
    outcomes_added = 0

    for symbol, asset_id in symbol_to_id.items():
        win_bias = ASSET_WIN_BIAS.get(symbol, 0.55)
        n_trades = random.randint(18, 28)

        for _ in range(n_trades):
            setup     = random.choice(SETUPS)
            direction = random.choice(DIRECTIONS)
            regime    = random.choice(REGIMES)
            catalyst  = random.choice(CATALYSTS)
            horizon   = random.choice(HORIZONS)
            ts        = _rand_ts(180)

            # apply per-setup bias on top of asset bias
            effective_p = (win_bias + SETUP_WIN_BIAS.get(setup, 0.55)) / 2
            win = random.random() < effective_p

            sig = _make_signal(asset_id, setup, direction, regime, catalyst, horizon, ts)
            db.add(sig)
            db.flush()

            outcome = _make_outcome(sig, asset_id, win)
            db.add(outcome)

            signals_added  += 1
            outcomes_added += 1

    db.commit()
    print(f"\nSeeded {signals_added} signals + {outcomes_added} outcomes across {len(symbol_to_id)} assets.")


if __name__ == "__main__":
    run()
