"""News sentiment scoring features."""

from __future__ import annotations

from typing import Sequence


def mean_sentiment(scores: Sequence[float]) -> float | None:
    """Return the mean sentiment score, or None if no scores."""
    if not scores:
        return None
    return sum(scores) / len(scores)


def sentiment_regime(score: float) -> str:
    """Classify a sentiment score into a qualitative bucket."""
    if score >= 0.5:
        return "very_positive"
    if score >= 0.1:
        return "positive"
    if score > -0.1:
        return "neutral"
    if score > -0.5:
        return "negative"
    return "very_negative"
