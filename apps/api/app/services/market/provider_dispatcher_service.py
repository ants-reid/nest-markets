"""ProviderDispatcherService — route requests to the best available data provider."""

from __future__ import annotations


from app.clients.market_data.base import MarketDataAdapter
from app.clients.news.base import NewsAdapter
from app.clients.fundamentals.base import FundamentalsAdapter
from app.clients.macro.base import MacroAdapter


class ProviderDispatcherService:
    """Selects the highest-priority healthy provider for each data type.

    Providers are tried in priority order.  If the primary is unreachable
    the dispatcher falls back to the next one.
    """

    def __init__(
        self,
        market_data_providers: list[MarketDataAdapter] | None = None,
        news_providers: list[NewsAdapter] | None = None,
        fundamentals_providers: list[FundamentalsAdapter] | None = None,
        macro_providers: list[MacroAdapter] | None = None,
    ) -> None:
        self._market_data: list[MarketDataAdapter] = market_data_providers or []
        self._news: list[NewsAdapter] = news_providers or []
        self._fundamentals: list[FundamentalsAdapter] = fundamentals_providers or []
        self._macro: list[MacroAdapter] = macro_providers or []

    def get_market_data_provider(self) -> MarketDataAdapter | None:
        """Return the first registered market data provider."""
        return self._market_data[0] if self._market_data else None

    def get_news_provider(self) -> NewsAdapter | None:
        """Return the first registered news provider."""
        return self._news[0] if self._news else None

    def get_fundamentals_provider(self) -> FundamentalsAdapter | None:
        """Return the first registered fundamentals provider."""
        return self._fundamentals[0] if self._fundamentals else None

    def get_macro_provider(self) -> MacroAdapter | None:
        """Return the first registered macro provider."""
        return self._macro[0] if self._macro else None

    def register_market_data(self, adapter: MarketDataAdapter) -> None:
        self._market_data.append(adapter)

    def register_news(self, adapter: NewsAdapter) -> None:
        self._news.append(adapter)

    def register_fundamentals(self, adapter: FundamentalsAdapter) -> None:
        self._fundamentals.append(adapter)

    def register_macro(self, adapter: MacroAdapter) -> None:
        self._macro.append(adapter)
