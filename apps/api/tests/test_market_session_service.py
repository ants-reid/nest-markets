"""MH-COCKPIT-01-A — Tests for market_session_service."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.market_session_service import get_market_snapshot


def _market(snapshot: dict, code: str) -> dict:
    return next(m for m in snapshot["markets"] if m["code"] == code)


def test_snapshot_includes_all_known_markets():
    snap = get_market_snapshot(datetime(2026, 5, 4, 14, 0, tzinfo=timezone.utc))
    codes = {m["code"] for m in snap["markets"]}
    assert codes == {"FX", "NYSE", "LSE", "TSE"}
    assert "advisory" in snap and "operator hint" in snap["advisory"].lower()


def test_nyse_open_during_regular_session_monday():
    # Monday 14:30 UTC == 10:30 ET (DST), inside 09:30–16:00 ET.
    snap = get_market_snapshot(datetime(2026, 5, 4, 14, 30, tzinfo=timezone.utc))
    nyse = _market(snap, "NYSE")
    assert nyse["is_open"] is True


def test_nyse_closed_on_saturday():
    snap = get_market_snapshot(datetime(2026, 5, 2, 14, 30, tzinfo=timezone.utc))
    nyse = _market(snap, "NYSE")
    assert nyse["is_open"] is False


def test_nyse_closed_outside_regular_hours():
    # Monday 03:00 UTC == 23:00 prev-day ET — closed.
    snap = get_market_snapshot(datetime(2026, 5, 4, 3, 0, tzinfo=timezone.utc))
    nyse = _market(snap, "NYSE")
    assert nyse["is_open"] is False


def test_lse_open_at_10am_local():
    # Monday 10:00 BST == 09:00 UTC (May, DST in effect).
    snap = get_market_snapshot(datetime(2026, 5, 4, 9, 0, tzinfo=timezone.utc))
    lse = _market(snap, "LSE")
    assert lse["is_open"] is True


def test_tse_open_during_window():
    # Tuesday 02:00 UTC == 11:00 JST.
    snap = get_market_snapshot(datetime(2026, 5, 5, 2, 0, tzinfo=timezone.utc))
    tse = _market(snap, "TSE")
    assert tse["is_open"] is True


def test_tse_closed_on_sunday():
    snap = get_market_snapshot(datetime(2026, 5, 3, 2, 0, tzinfo=timezone.utc))
    tse = _market(snap, "TSE")
    assert tse["is_open"] is False


def test_fx_closed_saturday_morning():
    # Saturday 10:00 UTC.
    snap = get_market_snapshot(datetime(2026, 5, 2, 10, 0, tzinfo=timezone.utc))
    fx = _market(snap, "FX")
    assert fx["is_open"] is False


def test_fx_open_sunday_evening():
    # Sunday 23:00 UTC — after 22:00 roll.
    snap = get_market_snapshot(datetime(2026, 5, 3, 23, 0, tzinfo=timezone.utc))
    fx = _market(snap, "FX")
    assert fx["is_open"] is True


def test_fx_closed_friday_late():
    # Friday 23:00 UTC — after 22:00 close.
    snap = get_market_snapshot(datetime(2026, 5, 1, 23, 0, tzinfo=timezone.utc))
    fx = _market(snap, "FX")
    assert fx["is_open"] is False


def test_fx_open_midweek():
    snap = get_market_snapshot(datetime(2026, 5, 6, 12, 0, tzinfo=timezone.utc))
    fx = _market(snap, "FX")
    assert fx["is_open"] is True


def test_naive_datetime_is_treated_as_utc():
    snap = get_market_snapshot(datetime(2026, 5, 4, 14, 30))
    nyse = _market(snap, "NYSE")
    assert nyse["is_open"] is True


def test_default_now_runs_without_error():
    snap = get_market_snapshot()
    assert "as_of_utc" in snap
    assert len(snap["markets"]) == 4
