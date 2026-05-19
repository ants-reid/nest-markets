"""ExecutionQualityLabeler — assess execution quality vs the signal price."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionQualityRecord:
    """Inputs for execution quality assessment."""

    trade_id: str
    signal_price: float     # price at signal generation
    fill_price: float       # actual fill price
    side: str               # "long" or "short"


@dataclass(frozen=True)
class ExecutionQualityLabel:
    """Execution quality assessment."""

    trade_id: str
    slippage_pct: float     # fill vs signal price as fraction
    slippage_direction: str # "favourable", "adverse", "neutral"
    quality_grade: str      # "excellent", "good", "acceptable", "poor"


class ExecutionQualityLabeler:
    """Compare fill price to signal price and grade execution quality."""

    def label(self, record: ExecutionQualityRecord) -> ExecutionQualityLabel:
        if record.signal_price == 0:
            raise ValueError("signal_price cannot be zero")

        raw_slip = (record.fill_price - record.signal_price) / record.signal_price
        # For longs, a higher fill price is adverse; for shorts, it's favourable
        if record.side == "long":
            slippage = raw_slip
        else:
            slippage = -raw_slip

        if slippage < -0.001:
            direction = "favourable"
        elif slippage > 0.001:
            direction = "adverse"
        else:
            direction = "neutral"

        abs_slip = abs(slippage)
        if abs_slip <= 0.0005:
            grade = "excellent"
        elif abs_slip <= 0.002:
            grade = "good"
        elif abs_slip <= 0.005:
            grade = "acceptable"
        else:
            grade = "poor"

        return ExecutionQualityLabel(
            trade_id=record.trade_id,
            slippage_pct=slippage,
            slippage_direction=direction,
            quality_grade=grade,
        )
