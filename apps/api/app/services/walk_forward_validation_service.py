"""Deterministic walk-forward and out-of-sample validation helpers (MH-17)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import gcd
from statistics import pstdev
from typing import Any

from app.services.strategy_result_quality_service import compute_result_quality


@dataclass(frozen=True)
class WalkForwardSplit:
    label: str
    start: datetime
    end: datetime
    percentage: int


@dataclass(frozen=True)
class RollingFold:
    fold_index: int
    splits: list[WalkForwardSplit]


def build_date_splits(
    *,
    date_from: datetime,
    date_to: datetime,
    in_sample_pct: int = 60,
    validation_pct: int = 20,
    out_of_sample_pct: int = 20,
) -> list[WalkForwardSplit]:
    _validate_split_inputs(
        date_from=date_from,
        date_to=date_to,
        in_sample_pct=in_sample_pct,
        validation_pct=validation_pct,
        out_of_sample_pct=out_of_sample_pct,
    )

    total_seconds = (date_to - date_from).total_seconds()
    in_seconds = total_seconds * (in_sample_pct / 100.0)
    validation_seconds = total_seconds * (validation_pct / 100.0)

    in_end = date_from + timedelta(seconds=in_seconds)
    validation_end = in_end + timedelta(seconds=validation_seconds)

    splits = [
        WalkForwardSplit(
            label="in_sample",
            start=date_from,
            end=in_end,
            percentage=in_sample_pct,
        ),
        WalkForwardSplit(
            label="validation",
            start=in_end,
            end=validation_end,
            percentage=validation_pct,
        ),
        WalkForwardSplit(
            label="out_of_sample",
            start=validation_end,
            end=date_to,
            percentage=out_of_sample_pct,
        ),
    ]

    for split in splits:
        if split.end <= split.start:
            raise ValueError("Each walk-forward split must have positive duration.")

    return splits


def build_rolling_fold_splits(
    *,
    date_from: datetime,
    date_to: datetime,
    fold_count: int = 3,
    in_sample_pct: int = 60,
    validation_pct: int = 20,
    out_of_sample_pct: int = 20,
) -> list[RollingFold]:
    _validate_split_inputs(
        date_from=date_from,
        date_to=date_to,
        in_sample_pct=in_sample_pct,
        validation_pct=validation_pct,
        out_of_sample_pct=out_of_sample_pct,
    )
    if fold_count <= 0:
        raise ValueError("fold_count must be greater than 0.")

    in_units, validation_units, out_units = _simplify_split_units(
        in_sample_pct=in_sample_pct,
        validation_pct=validation_pct,
        out_of_sample_pct=out_of_sample_pct,
    )
    total_units = in_units + validation_units + out_units
    segment_count = total_units + fold_count - 1

    total_seconds = (date_to - date_from).total_seconds()
    segment_seconds = total_seconds / segment_count
    boundaries = [
        date_from + timedelta(seconds=segment_seconds * idx)
        for idx in range(segment_count + 1)
    ]

    folds: list[RollingFold] = []
    for fold_index in range(fold_count):
        start_idx = fold_index
        in_start = boundaries[start_idx]
        in_end = boundaries[start_idx + in_units]
        validation_end = boundaries[start_idx + in_units + validation_units]
        out_end = boundaries[start_idx + total_units]
        splits = [
            WalkForwardSplit(
                label="in_sample",
                start=in_start,
                end=in_end,
                percentage=in_sample_pct,
            ),
            WalkForwardSplit(
                label="validation",
                start=in_end,
                end=validation_end,
                percentage=validation_pct,
            ),
            WalkForwardSplit(
                label="out_of_sample",
                start=validation_end,
                end=out_end,
                percentage=out_of_sample_pct,
            ),
        ]
        if any(split.end <= split.start for split in splits):
            raise ValueError("Each rolling fold split must have positive duration.")
        folds.append(RollingFold(fold_index=fold_index + 1, splits=splits))

    return folds


def _validate_split_inputs(
    *,
    date_from: datetime,
    date_to: datetime,
    in_sample_pct: int,
    validation_pct: int,
    out_of_sample_pct: int,
) -> None:
    if date_to <= date_from:
        raise ValueError("date_from must be before date_to.")

    percentages = [in_sample_pct, validation_pct, out_of_sample_pct]
    if any(v <= 0 for v in percentages):
        raise ValueError("All walk-forward split percentages must be > 0.")

    if sum(percentages) != 100:
        raise ValueError("Walk-forward split percentages must total 100.")


def calculate_period_metrics(
    *,
    period_label: str,
    trades: list[dict[str, Any]],
    starting_capital: float,
) -> dict[str, Any]:
    total_trades = len(trades)
    wins = sum(1 for t in trades if t.get("net_pnl", 0.0) > 0)
    win_rate = (wins / total_trades) if total_trades > 0 else None

    net_pnls = [float(t.get("net_pnl", 0.0)) for t in trades]
    net_profit = sum(v for v in net_pnls if v > 0)
    net_loss = abs(sum(v for v in net_pnls if v < 0))
    net_profit_factor = (net_profit / net_loss) if net_loss > 0 else None
    net_total_return_pct = (
        (sum(net_pnls) / starting_capital) * 100.0 if starting_capital > 0 else 0.0
    )

    max_drawdown_pct = _max_drawdown_from_pnls(starting_capital=starting_capital, pnls=net_pnls)
    confidence_inputs_level = _worst_cost_sensitivity(trades)
    quality = compute_result_quality(
        total_trades=total_trades,
        net_profit_factor=net_profit_factor,
        net_total_return_pct=net_total_return_pct,
        max_drawdown_pct=max_drawdown_pct,
        cost_sensitivity_level=confidence_inputs_level,
        high_cost_net_total_return_pct=net_total_return_pct,
        high_cost_net_profit_factor=net_profit_factor,
        monthly_returns=None,
        asset_count=1,
        timeframe_count=1,
    )

    return {
        "period": period_label,
        "total_trades": total_trades,
        "win_rate": round(win_rate, 6) if win_rate is not None else None,
        "net_profit_factor": round(net_profit_factor, 6) if net_profit_factor is not None else None,
        "net_total_return_pct": round(net_total_return_pct, 6),
        "max_drawdown_pct": round(max_drawdown_pct, 6),
        "research_confidence_score": quality["research_confidence_score"],
        "quality_grade": quality["quality_grade"],
    }


def calculate_walk_forward_summary(
    *,
    in_sample_metrics: dict[str, Any],
    validation_metrics: dict[str, Any],
    out_of_sample_metrics: dict[str, Any],
) -> dict[str, Any]:
    in_return = _f(in_sample_metrics.get("net_total_return_pct"))
    validation_return = _f(validation_metrics.get("net_total_return_pct"))
    out_return = _f(out_of_sample_metrics.get("net_total_return_pct"))

    in_pf = _f(in_sample_metrics.get("net_profit_factor"))
    out_pf = _f(out_of_sample_metrics.get("net_profit_factor"))

    in_conf = _f(in_sample_metrics.get("research_confidence_score"))
    out_conf = _f(out_of_sample_metrics.get("research_confidence_score"))

    in_dd = _f(in_sample_metrics.get("max_drawdown_pct"))
    out_dd = _f(out_of_sample_metrics.get("max_drawdown_pct"))
    out_trades = int(out_of_sample_metrics.get("total_trades") or 0)

    return_degradation_pct = _degradation_pct(in_return, out_return)
    profit_factor_degradation_pct = _degradation_pct(in_pf, out_pf)
    confidence_degradation_pct = _degradation_pct(in_conf, out_conf)

    stability_score = 100
    warnings: list[str] = []

    if out_return < 0:
        stability_score -= 30
        warnings.append("Out-of-sample performance degraded materially")

    if out_pf < 1.0:
        stability_score -= 20
        warnings.append("Out-of-sample profit factor below 1.0")

    if return_degradation_pct > 50:
        stability_score -= 20
        if "Out-of-sample performance degraded materially" not in warnings:
            warnings.append("Out-of-sample performance degraded materially")

    if in_dd > 0 and out_dd > (in_dd * 1.5):
        stability_score -= 15
        warnings.append("Out-of-sample drawdown materially worse")

    if out_trades < 30:
        stability_score -= 20
        warnings.append("Out-of-sample trade count too low")

    if in_return > 20 and out_return <= 0:
        stability_score -= 15
        warnings.append("In-sample results may be overfit")

    stability_score = int(max(0, min(100, stability_score)))
    if stability_score >= 75:
        stability_grade = "stable"
    elif stability_score >= 50:
        stability_grade = "mixed"
    else:
        stability_grade = "unstable"

    out_of_sample_pass = (
        stability_score >= 75
        and out_return > 0
        and out_pf >= 1.0
        and out_trades >= 30
    )

    warnings.append("Research only, not approved for paper or live trading")

    return {
        "in_sample_return": round(in_return, 6),
        "validation_return": round(validation_return, 6),
        "out_of_sample_return": round(out_return, 6),
        "out_of_sample_profit_factor": round(out_pf, 6),
        "return_degradation_pct": round(return_degradation_pct, 6),
        "profit_factor_degradation_pct": round(profit_factor_degradation_pct, 6),
        "confidence_degradation_pct": round(confidence_degradation_pct, 6),
        "validation_stability_score": stability_score,
        "validation_stability_grade": stability_grade,
        "out_of_sample_pass": out_of_sample_pass,
        "paper_trade_ready": False,
        "live_ready": False,
        "warnings": warnings,
    }


def calculate_multi_fold_summary(
    fold_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    if not fold_summaries:
        return {
            "fold_count": 0,
            "stable_fold_ratio": 0.0,
            "average_validation_stability_score": 0.0,
            "stability_dispersion": 0.0,
            "average_return_degradation_pct": 0.0,
            "average_confidence_degradation_pct": 0.0,
            "rolling_validation_grade": "unstable",
            "rolling_out_of_sample_pass": False,
            "warnings": ["Research only, not approved for paper or live trading"],
        }

    stability_scores = [_f(s.get("validation_stability_score")) for s in fold_summaries]
    return_degradations = [_f(s.get("return_degradation_pct")) for s in fold_summaries]
    confidence_degradations = [_f(s.get("confidence_degradation_pct")) for s in fold_summaries]
    stable_count = sum(1 for s in fold_summaries if str(s.get("validation_stability_grade")) == "stable")
    mixed_count = sum(1 for s in fold_summaries if str(s.get("validation_stability_grade")) == "mixed")
    unstable_count = sum(1 for s in fold_summaries if str(s.get("validation_stability_grade")) == "unstable")
    pass_count = sum(1 for s in fold_summaries if bool(s.get("out_of_sample_pass")))

    avg_stability = sum(stability_scores) / len(stability_scores)
    stable_ratio = stable_count / len(fold_summaries)
    dispersion = pstdev(stability_scores) if len(stability_scores) > 1 else 0.0
    avg_return_degradation = sum(return_degradations) / len(return_degradations)
    avg_confidence_degradation = sum(confidence_degradations) / len(confidence_degradations)

    if avg_stability >= 80 and stable_ratio >= 0.67:
        rolling_grade = "stable"
    elif avg_stability >= 55 and (stable_count + mixed_count) >= max(1, len(fold_summaries) // 2):
        rolling_grade = "mixed"
    else:
        rolling_grade = "unstable"

    warnings: list[str] = []
    if rolling_grade == "unstable" or unstable_count > 0:
        warnings.append("Performance unstable across rolling folds")
    if dispersion > 20:
        warnings.append("Validation stability varies materially across folds")
    if avg_return_degradation > 50:
        warnings.append("Average out-of-sample degradation is high")
    if stable_ratio < 0.5:
        warnings.append("Less than half of folds are stable")
    if pass_count < len(fold_summaries):
        warnings.append("Not all out-of-sample folds passed deterministic thresholds")
    warnings.append("Research only, not approved for paper or live trading")

    return {
        "fold_count": len(fold_summaries),
        "stable_fold_ratio": round(stable_ratio, 6),
        "average_validation_stability_score": round(avg_stability, 6),
        "stability_dispersion": round(dispersion, 6),
        "average_return_degradation_pct": round(avg_return_degradation, 6),
        "average_confidence_degradation_pct": round(avg_confidence_degradation, 6),
        "rolling_validation_grade": rolling_grade,
        "rolling_out_of_sample_pass": pass_count == len(fold_summaries),
        "warnings": warnings,
    }


def _max_drawdown_from_pnls(*, starting_capital: float, pnls: list[float]) -> float:
    equity = float(starting_capital)
    peak = equity
    max_dd = 0.0
    for pnl in pnls:
        equity += float(pnl)
        if equity > peak:
            peak = equity
        if peak > 0:
            dd = ((peak - equity) / peak) * 100.0
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _worst_cost_sensitivity(trades: list[dict[str, Any]]) -> str:
    rank = {"low": 0, "medium": 1, "high": 2, "loss_sensitive": 3}
    worst = "low"
    worst_rank = 0
    for t in trades:
        level = str(t.get("cost_sensitivity_level") or "low")
        level_rank = rank.get(level, 1)
        if level_rank > worst_rank:
            worst = level
            worst_rank = level_rank
    return worst


def _degradation_pct(in_sample_value: float, out_of_sample_value: float) -> float:
    base = abs(in_sample_value)
    if base <= 1e-9:
        return 0.0
    return max(0.0, ((in_sample_value - out_of_sample_value) / base) * 100.0)


def _simplify_split_units(
    *,
    in_sample_pct: int,
    validation_pct: int,
    out_of_sample_pct: int,
) -> tuple[int, int, int]:
    common = gcd(gcd(in_sample_pct, validation_pct), out_of_sample_pct)
    return (
        in_sample_pct // common,
        validation_pct // common,
        out_of_sample_pct // common,
    )


def _f(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
