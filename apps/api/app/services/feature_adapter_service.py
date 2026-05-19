"""Thin adapter from ORM market data models to deterministic feature input."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models.bar import Bar
from app.db.models.quote import Quote
from app.services.feature_service import (
    BarInput,
    FeatureInput,
    FeatureSnapshotPayload,
    QuoteInput,
    build_feature_snapshot,
)


@dataclass(frozen=True)
class FeatureAdapterRequest:
    """Input request used by the feature adapter."""

    asset_id: uuid.UUID
    timeframe: str
    bar_limit: int = 300
    quote_limit: int = 50


class FeatureAdapterService:
    """Loads ORM bars/quotes and maps them into deterministic feature input."""

    def __init__(self, session: Session) -> None:
        """Initialize adapter with a SQLAlchemy session."""
        self.session = session

    def build_snapshot(self, request: FeatureAdapterRequest) -> FeatureSnapshotPayload:
        """Build feature snapshot from ORM rows without persistence."""
        bars = self.load_bars(
            asset_id=request.asset_id,
            timeframe=request.timeframe,
            limit=request.bar_limit,
        )
        quotes = self.load_quotes(asset_id=request.asset_id, limit=request.quote_limit)

        bar_inputs = [self.map_bar_to_input(bar) for bar in bars]

        quote_inputs: list[QuoteInput] = []
        for quote in quotes:
            mapped = self.map_quote_to_input(quote)
            if mapped is not None:
                quote_inputs.append(mapped)

        payload = FeatureInput(
            bars=bar_inputs,
            quotes=quote_inputs or None,
            context={
                "asset_id": str(request.asset_id),
                "timeframe": request.timeframe,
            },
        )
        return build_feature_snapshot(payload)

    def load_bars(self, asset_id: uuid.UUID, timeframe: str, limit: int) -> list[Bar]:
        """Load latest bars for an asset/timeframe and return oldest-to-newest ordering."""
        if limit <= 0:
            raise ValueError("limit must be positive")

        statement: Select[tuple[Bar]] = (
            select(Bar)
            .where(Bar.asset_id == asset_id, Bar.timeframe == timeframe)
            .order_by(Bar.ts.desc())
            .limit(limit)
        )
        bars = list(self.session.execute(statement).scalars().all())
        return sorted(bars, key=lambda bar: bar.ts)

    def load_quotes(self, asset_id: uuid.UUID, limit: int) -> list[Quote]:
        """Load latest quotes for an asset and return oldest-to-newest ordering."""
        if limit <= 0:
            raise ValueError("limit must be positive")

        statement: Select[tuple[Quote]] = (
            select(Quote)
            .where(Quote.asset_id == asset_id)
            .order_by(Quote.ts.desc())
            .limit(limit)
        )
        quotes = list(self.session.execute(statement).scalars().all())
        return sorted(quotes, key=lambda quote: quote.ts)

    def map_bar_to_input(self, bar: Bar) -> BarInput:
        """Map a Bar ORM row to BarInput explicitly by field name."""
        return BarInput(
            open=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close),
            volume=float(bar.volume) if bar.volume is not None else 0.0,
        )

    def map_quote_to_input(self, quote: Quote) -> QuoteInput | None:
        """Map a Quote ORM row to QuoteInput, skipping incomplete quotes safely."""
        if quote.bid is None or quote.ask is None:
            return None
        bid = float(quote.bid)
        ask = float(quote.ask)
        if bid <= 0.0 or ask <= 0.0 or ask <= bid:
            return None

        return QuoteInput(
            bid=bid,
            ask=ask,
            bid_size=None,
            ask_size=None,
        )
