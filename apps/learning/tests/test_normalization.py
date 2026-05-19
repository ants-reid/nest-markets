"""Phase 6 — normalisation service tests."""

from __future__ import annotations

from apps.learning.services.normalization.symbol_mapper import SymbolMapper
from apps.learning.services.normalization.news_normalizer import NewsNormalizer


class TestSymbolMapper:
    def setup_method(self):
        self.mapper = SymbolMapper()

    def test_uppercase_passthrough(self):
        assert self.mapper.normalise("aapl") == "AAPL"

    def test_whitespace_stripped(self):
        assert self.mapper.normalise("  MSFT  ") == "MSFT"

    def test_btc_override(self):
        assert self.mapper.normalise("BTC/USD") == "BTCUSD"

    def test_batch_normalise(self):
        result = self.mapper.batch_normalise(["aapl", "BTC/USD", "spy"])
        assert result == ["AAPL", "BTCUSD", "SPY"]

    def test_custom_override(self):
        mapper = SymbolMapper(overrides={"XYZW": "XYZ"})
        assert mapper.normalise("xyzw") == "XYZ"


class TestNewsNormalizer:
    def setup_method(self):
        self.norm = NewsNormalizer()

    def test_from_finnhub(self):
        raw = {
            "id": 42,
            "headline": "Fed raises rates",
            "source": "Reuters",
            "datetime": 1700000000,
            "summary": "Summary text",
            "url": "https://example.com",
            "related": "AAPL,MSFT",
        }
        article = self.norm.from_finnhub(raw)
        assert article.headline == "Fed raises rates"
        assert "AAPL" in article.tickers
        assert article.external_id == "42"

    def test_from_alpaca(self):
        raw = {
            "id": "abc123",
            "headline": "AAPL beats earnings",
            "source": "Bloomberg",
            "created_at": "2024-01-15T10:30:00",
            "symbols": ["AAPL"],
        }
        article = self.norm.from_alpaca(raw)
        assert article.headline == "AAPL beats earnings"
        assert "AAPL" in article.tickers
