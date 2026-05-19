"""SymbolMapper — normalise provider-specific ticker symbols.

Different providers use different formats for the same instrument:
  - Tiingo:      "AAPL"
  - Alpaca:      "AAPL"
  - IBKR (STK):  "AAPL"
  - Crypto:      "BTC/USD" vs "BTCUSD"

SymbolMapper provides a canonical form and can be extended with
exchange/asset-class-aware rules as more providers are onboarded.
"""

from __future__ import annotations

_OVERRIDES: dict[str, str] = {
    "BTC/USD": "BTCUSD",
    "ETH/USD": "ETHUSD",
}


class SymbolMapper:
    """Normalise ticker symbols to a canonical uppercase form."""

    def __init__(self, overrides: dict[str, str] | None = None) -> None:
        self._overrides = {**_OVERRIDES, **(overrides or {})}

    def normalise(self, raw: str) -> str:
        """Return the canonical symbol for *raw*."""
        upper = raw.strip().upper()
        return self._overrides.get(upper, upper)

    def batch_normalise(self, symbols: list[str]) -> list[str]:
        return [self.normalise(s) for s in symbols]
