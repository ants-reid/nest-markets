"""ScoreBucketService — assign a scoring bucket to an opportunity."""

from __future__ import annotations


class ScoreBucketService:
    """Derive the scoring bucket string for a (asset_class, strategy, timeframe) triple.

    Bucket format: ``"{asset_class}/{strategy}/{timeframe}"``
    e.g. ``"equity/momentum/1D"``
    """

    def assign(
        self,
        asset_class: str,
        strategy: str,
        timeframe: str,
    ) -> str:
        """Return the canonical bucket identifier."""
        return f"{asset_class.lower()}/{strategy.lower()}/{timeframe.upper()}"

    def parse(self, bucket: str) -> tuple[str, str, str]:
        """Split a bucket string into (asset_class, strategy, timeframe)."""
        parts = bucket.split("/")
        if len(parts) != 3:
            raise ValueError(f"Invalid bucket format: {bucket!r}")
        return parts[0], parts[1], parts[2]
