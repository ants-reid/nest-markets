"""Tests for MH-COCKPIT-06-A notifications-digest aggregator service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.db.session import SessionLocal
from app.services.incident_log_service import record_incident
from app.services.notifications_digest_service import (
    NotificationsDigestError,
    get_notifications_digest,
)


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
    from app.db.models.incident_log import IncidentLog

    session.query(IncidentLog).filter(
        IncidentLog.code.like("test.cockpit06.%")
    ).delete(synchronize_session=False)
    session.commit()
    yield
    session.query(IncidentLog).filter(
        IncidentLog.code.like("test.cockpit06.%")
    ).delete(synchronize_session=False)
    session.commit()


def _seed(session, *, source, severity, code_suffix):
    record_incident(
        session,
        severity=severity,
        code=f"test.cockpit06.{code_suffix}",
        title=f"test {code_suffix}",
        source=source,
    )
    session.commit()


def test_empty_digest_shape(session):
    now = datetime.now(timezone.utc)
    result = get_notifications_digest(
        session,
        hours=4,
        min_severity="warn",
        limit=10,
        now_utc=now,
    )
    assert result["hours"] == 4
    assert result["min_severity"] == "warn"
    assert result["limit"] == 10
    assert "operator-facing only" in result["advisory"]
    assert isinstance(result["totals"]["by_severity"], dict)


def test_attention_floor_excludes_lower_severities(session):
    _seed(session, source="cockpit06_src_a", severity="info", code_suffix="i")
    _seed(session, source="cockpit06_src_a", severity="warn", code_suffix="w")
    _seed(session, source="cockpit06_src_b", severity="error", code_suffix="e")
    now = datetime.now(timezone.utc) + timedelta(seconds=5)

    result = get_notifications_digest(
        session, hours=2, min_severity="warn", limit=10, now_utc=now
    )

    severities = {r["severity"] for r in result["attention"]}
    assert "info" not in severities
    assert "warn" in severities
    assert "error" in severities
    # Counts should still include info
    assert result["totals"]["by_severity"]["info"] >= 1


def test_highest_severity_is_critical_when_present(session):
    _seed(session, source="cockpit06_src_c", severity="warn", code_suffix="w2")
    _seed(session, source="cockpit06_src_c", severity="critical", code_suffix="c1")
    now = datetime.now(timezone.utc) + timedelta(seconds=5)

    result = get_notifications_digest(
        session, hours=2, min_severity="info", limit=10, now_utc=now
    )
    assert result["highest_severity"] == "critical"


def test_limit_clamped(session):
    for i in range(5):
        _seed(
            session,
            source="cockpit06_src_d",
            severity="error",
            code_suffix=f"l{i}",
        )
    now = datetime.now(timezone.utc) + timedelta(seconds=5)
    result = get_notifications_digest(
        session, hours=2, min_severity="warn", limit=999, now_utc=now
    )
    assert result["limit"] == 50  # MAX_LIMIT
    assert len(result["attention"]) <= 50


def test_invalid_min_severity_rejected(session):
    with pytest.raises(NotificationsDigestError):
        get_notifications_digest(
            session, hours=4, min_severity="bogus", limit=10
        )


def test_invalid_hours_rejected(session):
    with pytest.raises(NotificationsDigestError):
        get_notifications_digest(
            session, hours=0, min_severity="warn", limit=10
        )


def test_hours_clamped_to_max(session):
    now = datetime.now(timezone.utc)
    result = get_notifications_digest(
        session, hours=10_000, min_severity="warn", limit=10, now_utc=now
    )
    assert result["hours"] == 24 * 7
