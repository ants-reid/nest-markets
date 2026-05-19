"""Compatibility wrapper for the news client scaffold.

Build Plan 2 expects a market-data scoped news client module. The concrete
implementation currently lives under app.clients.news.news_client.
"""

from app.clients.news.news_client import NewsClient, NewsItem, PlaceholderNewsClient, PolygonNewsClient, get_news_client

__all__ = ["NewsClient", "NewsItem", "PlaceholderNewsClient", "PolygonNewsClient", "get_news_client"]
