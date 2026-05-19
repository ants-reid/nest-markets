"""Phase 5 — macro adapter tests."""

from __future__ import annotations

import asyncio
from datetime import date

import pytest

from app.clients.macro.base import MacroAdapter, MacroDataPoint
from app.clients.macro.fred import FREDAdapter
from app.clients.macro.mock import MockMacroAdapter


def test_abstract_interface_cannot_be_instantiated():
    with pytest.raises(TypeError):
        MacroAdapter()  # type: ignore[abstract]


def test_fred_stub_raises():
    with pytest.raises(NotImplementedError):
        asyncio.run(
            FREDAdapter().fetch_series("FEDFUNDS", start=date(2024, 1, 1), end=date(2024, 3, 1))
        )


def test_fred_provider_name():
    assert FREDAdapter().provider_name == "fred"


def test_fred_list_series():
    series = asyncio.run(FREDAdapter().list_series())
    assert "FEDFUNDS" in series


def test_mock_provider_name():
    assert MockMacroAdapter().provider_name == "mock"


def test_mock_returns_data_points():
    points = asyncio.run(
        MockMacroAdapter().fetch_series("FEDFUNDS", start=date(2023, 1, 1), end=date(2023, 6, 1))
    )
    assert len(points) >= 1
    assert all(isinstance(p, MacroDataPoint) for p in points)
    assert all(p.series_code == "FEDFUNDS" for p in points)


def test_mock_list_series():
    series = asyncio.run(MockMacroAdapter().list_series())
    assert isinstance(series, list)
    assert len(series) >= 1


def test_mock_health_check():
    ok = asyncio.run(MockMacroAdapter().health_check())
    assert ok is True
