"""Deterministic research-only quality scoring for Strategy Lab results (MH-16)."""

from __future__ import annotations

from typing import Any

QUALITY_RESULT_VERSION = "mh16_v1"


def score_sample_size(total_trades: int) -> int:
    if total_trades >= 500:
        return 100
    if total_trades >= 200:
        return 80
    if total_trades >= 100:
        return 60
    if total_trades >= 50:
        return 40
    return 20


def score_profitability(net_profit_factor: float | None, net_total_return_pct: float | None) -> int:
    pf = float(net_profit_factor) if net_profit_factor is not None else 0.0
    ret = float(net_total_return_pct) if net_total_return_pct is not None else 0.0

    if pf >= 1.5 and ret > 20:
        return 100
    if pf >= 1.25 and ret > 10:
        return 80
    if pf >= 1.1 and ret > 0:
        return 60
    if pf >= 1.0:
        return 40
    return 20


def score_drawdown(max_drawdown_pct: float | None) -> int:
    dd = float(max_drawdown_pct) if max_drawdown_pct is not None else 100.0
    if dd <= 5:
        return 100
    if dd <= 10:
        return 80
    if dd <= 15:
        return 60
    if dd <= 25:
        return 40
    return 20


def score_cost_sensitivity(cost_sensitivity_level: str | None) -> int:
    level = (cost_sensitivity_level or "").strip().lower()
    if level == "low":
        return 100
    if level == "medium":
        return 70
    if level in {"high", "loss_sensitive"}:
        return 30
    return 50


def score_consistency(monthly_returns: list[float] | None) -> int | None:
    if not monthly_returns:
        return None

    months = [float(v) for v in monthly_returns]
    positives = sum(1 for v in months if v > 0)
    ratio = positives / len(months)
    if ratio >= 0.8:
        return 90
    if ratio >= 0.65:
        return 75
    if ratio >= 0.5:
        return 60
    if ratio >= 0.35:
        return 45
    return 30


def derive_robustness_score(
    profitability_score: int,
    drawdown_score: int,
    cost_sensitivity_score: int,
    consistency_score: int | None,
) -> int:
    if consistency_score is None:
        score = (
            profitability_score * 0.45
            + drawdown_score * 0.30
            + cost_sensitivity_score * 0.25
        )
    else:
        score = (
            profitability_score * 0.35
            + drawdown_score * 0.25
            + cost_sensitivity_score * 0.20
            + consistency_score * 0.20
        )
    return int(round(max(0.0, min(100.0, score))))


def derive_overfitting_risk_score(
    *,
    total_trades: int,
    net_profit_factor: float | None,
    net_total_return_pct: float | None,
    high_cost_net_total_return_pct: float | None,
    high_cost_net_profit_factor: float | None,
    asset_count: int = 1,
    timeframe_count: int = 1,
) -> int:
    risk = 20
    pf = float(net_profit_factor) if net_profit_factor is not None else 0.0
    ret = float(net_total_return_pct) if net_total_return_pct is not None else 0.0
    high_ret = (
        float(high_cost_net_total_return_pct)
        if high_cost_net_total_return_pct is not None
        else None
    )
    high_pf = (
        float(high_cost_net_profit_factor)
        if high_cost_net_profit_factor is not None
        else None
    )

    if total_trades < 50:
        risk += 35
    elif total_trades < 100:
        risk += 20

    if ret > 30 and total_trades < 100:
        risk += 20

    if pf >= 2.0 and total_trades < 100:
        risk += 15

    if high_ret is not None and ret > 0 and high_ret < 0:
        risk += 20
    if high_pf is not None and pf >= 1.2 and high_pf < 1.0:
        risk += 10

    if asset_count <= 1 and timeframe_count <= 1:
        risk += 10

    return int(max(0, min(100, risk)))


def grade_from_confidence(confidence_score: float) -> str:
    if confidence_score >= 85:
        return "A"
    if confidence_score >= 70:
        return "B"
    if confidence_score >= 55:
        return "C"
    if confidence_score >= 40:
        return "D"
    return "F"


def compute_result_quality(
    *,
    total_trades: int,
    net_profit_factor: float | None,
    net_total_return_pct: float | None,
    max_drawdown_pct: float | None,
    cost_sensitivity_level: str | None,
    high_cost_net_total_return_pct: float | None = None,
    high_cost_net_profit_factor: float | None = None,
    monthly_returns: list[float] | None = None,
    asset_count: int = 1,
    timeframe_count: int = 1,
) -> dict[str, Any]:
    sample_size_score = score_sample_size(total_trades)
    profitability_score = score_profitability(net_profit_factor, net_total_return_pct)
    drawdown_score = score_drawdown(max_drawdown_pct)
    cost_sensitivity_score = score_cost_sensitivity(cost_sensitivity_level)
    consistency_score = score_consistency(monthly_returns)
    robustness_score = derive_robustness_score(
        profitability_score=profitability_score,
        drawdown_score=drawdown_score,
        cost_sensitivity_score=cost_sensitivity_score,
        consistency_score=consistency_score,
    )
    overfitting_risk_score = derive_overfitting_risk_score(
        total_trades=total_trades,
        net_profit_factor=net_profit_factor,
        net_total_return_pct=net_total_return_pct,
        high_cost_net_total_return_pct=high_cost_net_total_return_pct,
        high_cost_net_profit_factor=high_cost_net_profit_factor,
        asset_count=asset_count,
        timeframe_count=timeframe_count,
    )

    confidence = (
        sample_size_score * 0.25
        + profitability_score * 0.25
        + drawdown_score * 0.20
        + cost_sensitivity_score * 0.15
        + robustness_score * 0.15
    )
    confidence = round(max(0.0, min(100.0, confidence)), 2)
    quality_grade = grade_from_confidence(confidence)

    warnings: list[str] = []
    if sample_size_score <= 40:
        warnings.append("Low sample size")
    if cost_sensitivity_score <= 30:
        warnings.append("High execution-cost sensitivity")
    if drawdown_score <= 40:
        warnings.append("High drawdown")
    if profitability_score <= 40:
        warnings.append("Net profitability weak after costs")
    if overfitting_risk_score >= 70:
        warnings.append("High overfitting risk")
    warnings.append("Research only, not approved for paper or live trading")

    return {
        "result_quality_version": QUALITY_RESULT_VERSION,
        "sample_size_score": sample_size_score,
        "profitability_score": profitability_score,
        "drawdown_score": drawdown_score,
        "cost_sensitivity_score": cost_sensitivity_score,
        "consistency_score": consistency_score,
        "consistency_score_available": consistency_score is not None,
        "robustness_score": robustness_score,
        "overfitting_risk_score": overfitting_risk_score,
        "research_confidence_score": confidence,
        "quality_grade": quality_grade,
        "paper_trade_ready": False,
        "live_ready": False,
        "quality_warnings": warnings,
    }
