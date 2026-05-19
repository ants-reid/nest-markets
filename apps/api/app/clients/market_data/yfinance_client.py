"""Yahoo Finance market data client.

Implements the ``MarketDataClient`` protocol using ``yfinance``.
No API key required — suitable for development and MVP use.

Ticker mapping notes:
  - FX pairs (EURUSD, GBPUSD, USDJPY) are appended with ``=X`` for yfinance.
  - Commodity ETFs (GLD) and equity ETFs (SPY, QQQ) work as-is.
"""

from __future__ import annotations

import logging
from datetime import date

import yfinance as yf

from app.clients.market_data.polygon_client import BarData

_logger = logging.getLogger(__name__)

# yfinance interval strings for each internal timeframe key
_INTERVAL_MAP: dict[str, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "1h",   # yfinance has no 4h; fall back to 1h
    "1d": "1d",
    "day": "1d",
    "week": "1wk",
}

# FX pairs that need the ``=X`` suffix in Yahoo Finance
_FX_PAIRS = {
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "USDCHF", "NZDUSD", "EURJPY", "EURGBP",
}


def _to_yf_ticker(symbol: str) -> str:
    """Convert internal symbol to a yfinance-compatible ticker string."""
    upper = symbol.upper()
    if upper in _FX_PAIRS:
        return upper + "=X"
    return upper


class YFinanceClient:
    """Sync-friendly wrapper around ``yfinance`` implementing ``MarketDataClient``.

    ``get_bars`` runs the yfinance download synchronously (yfinance is not
    async-native) and wraps the result in the shared ``BarData`` dataclass.
    """

    async def get_bars(
        self,
        ticker: str,
        from_date: date,
        to_date: date,
        timeframe: str = "day",
    ) -> list[BarData]:
        """Fetch OHLCV bars from Yahoo Finance for *ticker*.

        Returns an empty list on any download error so the caller can
        degrade gracefully.
        """
        yf_ticker = _to_yf_ticker(ticker)
        interval = _INTERVAL_MAP.get(timeframe, "1d")

        try:
            df = yf.download(
                yf_ticker,
                start=from_date.isoformat(),
                end=to_date.isoformat(),
                interval=interval,
                progress=False,
                auto_adjust=True,
                threads=False,
            )
        except Exception as exc:
            _logger.warning("yfinance download failed for %s: %s", ticker, exc)
            return []

        if df is None or df.empty:
            _logger.debug("yfinance returned no data for %s", ticker)
            return []

        bars: list[BarData] = []
        for ts, row in df.iterrows():
            try:
                # Handle both MultiIndex and flat column DataFrames
                def _get(col: str) -> float:
                    if (col, yf_ticker) in df.columns:
                        return float(row[(col, yf_ticker)])
                    return float(row[col])

                ts_ms = int(ts.timestamp() * 1000)
                bars.append(
                    BarData(
                        ticker=ticker.upper(),
                        timestamp_ms=ts_ms,
                        open=_get("Open"),
                        high=_get("High"),
                        low=_get("Low"),
                        close=_get("Close"),
                        volume=_get("Volume"),
                        timeframe=timeframe,
                    )
                )
            except Exception as exc:
                _logger.debug("yfinance row parse error for %s: %s", ticker, exc)
                continue

        return bars
