"""Test fixtures for indicators."""

import os

import pytest

# Prevent APScheduler from starting during pytest runs
os.environ.setdefault("APP_ENV", "test")


@pytest.fixture
def sample_prices():
    """Generate sample price data for testing."""
    prices = [100.0]
    for i in range(1, 100):
        # Generate realistic price movement
        change = (i % 10 - 5) * 0.5
        prices.append(max(prices[-1] + change, 50.0))
    return prices


@pytest.fixture
def sample_bars(sample_prices):
    """Generate sample bar data for testing."""
    bars = []
    for price in sample_prices:
        bar = {
            "open": price,
            "high": price * 1.01,
            "low": price * 0.99,
            "close": price,
            "volume": 1000000,
        }
        bars.append(bar)
    return bars


@pytest.fixture
def sample_quotes():
    """Generate sample quote data for testing."""
    quotes = []
    for i in range(100):
        mid = 100 + (i * 0.1)
        quote = {
            "bid_price": mid - 0.05,
            "bid_size": 1000,
            "ask_price": mid + 0.05,
            "ask_size": 1000,
        }
        quotes.append(quote)
    return quotes
