"""Tests for seed_assets.py — QA-200: idempotent universe seeding."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from scripts.seed_assets import _UNIVERSE, seed_assets


def test_seed_universe_has_20_assets():
    """The universe definition must contain exactly 20 assets."""
    assert len(_UNIVERSE) == 20


def test_seed_inserts_all_when_empty():
    """When no assets exist, all 20 are inserted."""
    mock_session = MagicMock()
    mock_session.query.return_value.filter_by.return_value.first.return_value = None

    result = seed_assets(session=mock_session)

    assert result["inserted"] == 20
    assert result["skipped"] == 0
    assert mock_session.add.call_count == 20
    mock_session.commit.assert_called_once()


def test_seed_skips_existing_assets():
    """When all assets already exist, nothing is inserted."""
    from app.db.models.asset import Asset

    existing = MagicMock(spec=Asset)
    mock_session = MagicMock()
    mock_session.query.return_value.filter_by.return_value.first.return_value = existing

    result = seed_assets(session=mock_session)

    assert result["inserted"] == 0
    assert result["skipped"] == 20
    mock_session.add.assert_not_called()


def test_seed_partially_inserts_missing_assets():
    """When some assets exist, only missing ones are inserted."""
    def _first_side_effect():
        # Called each time filter_by().first() is called
        # We can't easily track which symbol per call with MagicMock chain,
        # so we test via total counts
        return None

    mock_session = MagicMock()
    call_count = [0]

    def first_side():
        call_count[0] += 1
        # First 3 calls return an existing asset; rest return None
        if call_count[0] <= 3:
            return MagicMock()
        return None

    mock_session.query.return_value.filter_by.return_value.first.side_effect = first_side

    result = seed_assets(session=mock_session)

    assert result["inserted"] == 17
    assert result["skipped"] == 3
    assert mock_session.add.call_count == 17


def test_seed_rollback_on_error():
    """On DB error, rollback is called and exception re-raised."""
    mock_session = MagicMock()
    mock_session.query.return_value.filter_by.return_value.first.return_value = None
    mock_session.commit.side_effect = RuntimeError("DB error")

    with pytest.raises(RuntimeError, match="DB error"):
        seed_assets(session=mock_session)

    mock_session.rollback.assert_called_once()
