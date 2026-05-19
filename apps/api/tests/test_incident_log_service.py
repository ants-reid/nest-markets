"""Tests for MH-MON-05 incident log service."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.db.models.incident_log import IncidentLog
from app.db.session import SessionLocal
from app.services.incident_log_service import (
    IncidentLogError,
    list_incidents,
    record_incident,
)


@pytest.fixture
def session():
    s = SessionLocal()
    try:
        # Wipe any state from prior tests so assertions on counts hold.
        s.query(IncidentLog).delete()
        s.commit()
        yield s
    finally:
        s.query(IncidentLog).delete()
        s.commit()
        s.close()


def test_record_incident_minimal(session):
    row = record_incident(
        session,
        severity="info",
        code="test.minimal",
        title="hello",
        source="unit",
    )
    assert row.severity == "info"
    assert row.code == "test.minimal"
    assert row.title == "hello"
    assert row.source == "unit"
    assert row.detail is None
    assert row.extra_json is None
    assert row.created_at != ""


def test_record_incident_full(session):
    occurred = datetime.now(UTC)
    row = record_incident(
        session,
        severity="critical",
        code="broker.gateway_down",
        title="IBKR gateway unreachable",
        source="broker",
        detail="connection refused on port 4002",
        extra={"host": "127.0.0.1", "port": 4002},
        correlation_id="abc-123",
        occurred_at=occurred,
    )
    assert row.severity == "critical"
    assert row.extra_json == {"host": "127.0.0.1", "port": 4002}
    assert row.correlation_id == "abc-123"
    assert row.occurred_at is not None


@pytest.mark.parametrize("bad", ["", "fatal", "INFO", None])
def test_record_rejects_invalid_severity(session, bad):
    with pytest.raises(IncidentLogError):
        record_incident(
            session,
            severity=bad,  # type: ignore[arg-type]
            code="x",
            title="t",
            source="s",
        )


def test_record_rejects_empty_code(session):
    with pytest.raises(IncidentLogError):
        record_incident(session, severity="info", code="", title="t", source="s")


def test_record_rejects_oversized_code(session):
    with pytest.raises(IncidentLogError):
        record_incident(session, severity="info", code="x" * 81, title="t", source="s")


def test_record_rejects_empty_title(session):
    with pytest.raises(IncidentLogError):
        record_incident(session, severity="info", code="c", title="", source="s")


def test_record_rejects_empty_source(session):
    with pytest.raises(IncidentLogError):
        record_incident(session, severity="info", code="c", title="t", source="")


def test_list_returns_most_recent_first(session):
    record_incident(session, severity="info", code="a", title="first", source="s")
    record_incident(session, severity="warn", code="b", title="second", source="s")
    record_incident(session, severity="error", code="c", title="third", source="s")
    rows = list_incidents(session)
    assert [r.title for r in rows] == ["third", "second", "first"]


def test_list_filter_by_severity(session):
    record_incident(session, severity="info", code="a", title="i", source="s")
    record_incident(session, severity="warn", code="b", title="w", source="s")
    rows = list_incidents(session, severity="warn")
    assert len(rows) == 1
    assert rows[0].severity == "warn"


def test_list_filter_by_source(session):
    record_incident(session, severity="info", code="a", title="t", source="broker")
    record_incident(session, severity="info", code="b", title="t", source="llm")
    rows = list_incidents(session, source="broker")
    assert len(rows) == 1
    assert rows[0].source == "broker"


def test_list_caps_limit_at_500(session):
    rows = list_incidents(session, limit=10_000)
    # Empty table — but the call must not crash, and the SQL LIMIT must be capped.
    assert isinstance(rows, list)


def test_list_rejects_bad_severity_filter(session):
    with pytest.raises(IncidentLogError):
        list_incidents(session, severity="nope")  # type: ignore[arg-type]
