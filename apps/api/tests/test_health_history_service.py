"""Tests for MH-MON-08-A health-history aggregator service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.db.session import SessionLocal
from app.services.health_history_service import (
    HealthHistoryError,
    get_health_history,
)
from app.services.incident_log_service import record_incident


@pytest.fixture()
def session():
    s = SessionLocal()
    try:
        yield s
        s.rollback()
    finally:
        s.close()


@pytest.fixture(autouse=True)
def _isolate_test_incidents(session):
    """Remove test-tagged incidents before and after each test."""
    from app.db.models.incident_log import IncidentLog

    session.query(IncidentLog).filter(
        IncidentLog.code.like("test.mon08.%")
    ).delete(synchronize_session=False)
    session.commit()
    yield
    session.query(IncidentLog).filter(
        IncidentLog.code.like("test.mon08.%")
    ).delete(synchronize_session=False)
    session.commit()


def _seed(session, *, source, severity, code_suffix, occurred_at=None):
    record_incident(
        session,
        severity=severity,
        code=f"test.mon08.{code_suffix}",
        title=f"test {code_suffix}",
        source=source,
        occurred_at=occurred_at,
    )
    session.commit()


def test_empty_returns_dense_timeseries(session):
    now = datetime.now(timezone.utc)
    result = get_health_history(
        session, hours=4, bucket_minutes=60, source="__nonexistent_test_source__", now_utc=now
    )
    assert result["hours"] == 4
    assert result["bucket_minutes"] == 60
    assert len(result["timeseries"]) == 4
    assert all(b["total"] == 0 for b in result["timeseries"])
    assert result["totals"]["incidents"] == 0
    assert "operator-facing only" in result["advisory"]


def test_counts_aggregate_by_bucket_and_severity(session):
    _seed(session, source="broker_test_mon08", severity="warn", code_suffix="a")
    _seed(session, source="broker_test_mon08", severity="error", code_suffix="b")
    _seed(session, source="llm_test_mon08", severity="info", code_suffix="c")
    now = datetime.now(timezone.utc) + timedelta(seconds=5)
    result = get_health_history(session, hours=2, bucket_minutes=60, now_utc=now)

    assert result["totals"]["incidents"] >= 3
    assert result["totals"]["by_severity"]["warn"] >= 1
    assert result["totals"]["by_severity"]["error"] >= 1
    assert result["totals"]["by_severity"]["info"] >= 1
    assert result["totals"]["by_source"].get("broker_test_mon08", 0) >= 2
    assert "broker_test_mon08" in result["last_per_source"]


def test_source_filter(session):
    _seed(session, source="broker_test_mon08", severity="warn", code_suffix="x")
    _seed(session, source="llm_test_mon08", severity="warn", code_suffix="y")
    now = datetime.now(timezone.utc) + timedelta(seconds=5)
    result = get_health_history(
        session, hours=2, bucket_minutes=60, source="broker_test_mon08", now_utc=now
    )
    assert result["filters"]["source"] == "broker_test_mon08"
    assert "llm_test_mon08" not in result["totals"]["by_source"]
    assert result["totals"]["by_source"].get("broker_test_mon08", 0) >= 1


def test_invalid_bucket_rejected(session):
    with pytest.raises(HealthHistoryError):
        get_health_history(session, hours=4, bucket_minutes=7)


def test_invalid_hours_rejected(session):
    with pytest.raises(HealthHistoryError):
        get_health_history(session, hours=0, bucket_minutes=60)


def test_hours_clamped_to_max(session):
    now = datetime.now(timezone.utc)
    result = get_health_history(session, hours=10_000, bucket_minutes=240, now_utc=now)
    assert result["hours"] == 24 * 7
    expected_buckets = (24 * 7 * 60) // 240
    assert len(result["timeseries"]) == expected_buckets
