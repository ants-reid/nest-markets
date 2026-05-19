"""MH-05 tests for research job orchestration routes and service behavior."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.enums import AssetClass
from app.db.models.asset import Asset
from app.db.models.research_job import ResearchJob
from app.db.session import SessionLocal, engine, get_db_session
from app.main import app
from app.services.research_job_service import ResearchJobService


def _seed_asset(session: Session, symbol: str = "AAPL") -> Asset:
    asset = Asset(symbol=symbol, name=symbol, asset_class=AssetClass.EQUITY, is_active=True)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


@pytest.fixture()
def db_session() -> Session:  # type: ignore[misc]
    schema_name = f"test_research_jobs_{uuid4().hex}"

    admin_conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    admin_conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
    admin_conn.close()

    conn = engine.connect()
    conn.execute(text(f'SET search_path TO "{schema_name}"'))
    conn.commit()
    Base.metadata.create_all(bind=conn)

    session = SessionLocal(bind=conn)
    try:
        yield session
    finally:
        session.close()
        conn.close()
        cleanup = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        cleanup.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        cleanup.close()


@pytest.fixture()
def client(db_session: Session) -> TestClient:  # type: ignore[misc]
    def _override():
        yield db_session

    app.dependency_overrides[get_db_session] = _override
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_create_import_job(client: TestClient, db_session: Session) -> None:
    _seed_asset(db_session, "AAPL")

    response = client.post(
        "/research/jobs/import",
        json={
            "assets": ["AAPL"],
            "timeframes": ["1d"],
            "requested_years": 1,
            "providers": ["yfinance"],
            "dry_run": True,
        },
    )
    assert response.status_code == 202, response.text
    body = response.json()["job"]
    assert body["job_type"] == "historical_import"
    assert body["status"] in {"completed", "partial"}

    jobs = db_session.execute(select(ResearchJob)).scalars().all()
    assert len(jobs) == 1


def test_create_quality_job(client: TestClient, db_session: Session) -> None:
    _seed_asset(db_session, "AAPL")

    response = client.post(
        "/research/jobs/quality/recalculate",
        json={"assets": ["AAPL"], "timeframes": ["1d"], "providers": ["yfinance"]},
    )
    assert response.status_code == 202, response.text
    body = response.json()["job"]
    assert body["job_type"] == "quality_recalculate"


def test_list_jobs(client: TestClient, db_session: Session) -> None:
    service = ResearchJobService(db_session)
    service.create_queued_job("historical_import", {"assets": ["AAPL"]}, progress_total=1)

    response = client.get("/research/jobs")
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_get_job_detail(client: TestClient, db_session: Session) -> None:
    service = ResearchJobService(db_session)
    job = service.create_queued_job("historical_import", {"assets": ["AAPL"]}, progress_total=1)

    response = client.get(f"/research/jobs/{job.id}")
    assert response.status_code == 200
    assert response.json()["job"]["id"] == str(job.id)


def test_cancel_queued_job(client: TestClient, db_session: Session) -> None:
    service = ResearchJobService(db_session)
    job = service.create_queued_job("historical_import", {"assets": ["AAPL"]}, progress_total=1)

    response = client.post(f"/research/jobs/{job.id}/cancel")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["job"]["status"] == "cancelled"


def test_retry_partial_job(client: TestClient, db_session: Session) -> None:
    service = ResearchJobService(db_session)
    job = service.create_queued_job(
        "quality_recalculate",
        {"assets": ["AAPL"], "timeframes": ["1d"], "providers": ["yfinance"]},
        progress_total=1,
    )
    job.status = "partial"
    db_session.commit()

    response = client.post(f"/research/jobs/{job.id}/retry")
    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    assert body["job"]["retry_of_job_id"] == str(job.id)


def test_running_job_cancel_returns_honest_message(db_session: Session) -> None:
    service = ResearchJobService(db_session)
    job = service.create_queued_job("historical_import", {"assets": ["AAPL"]}, progress_total=1)
    job.status = "running"
    db_session.commit()

    cancelled, message = service.cancel_job(job.id)
    assert cancelled is not None
    assert message == "cannot_cancel_running_sync_job"


def test_failed_job_retry_not_mutating_old_job(client: TestClient, db_session: Session) -> None:
    service = ResearchJobService(db_session)
    job = service.create_queued_job(
        "quality_recalculate",
        {"assets": ["AAPL"], "timeframes": ["1d"], "providers": ["yfinance"]},
        progress_total=1,
    )
    job.status = "failed"
    db_session.commit()

    response = client.post(f"/research/jobs/{job.id}/retry")
    assert response.status_code == 202

    rows = db_session.execute(select(ResearchJob).order_by(ResearchJob.created_at.asc())).scalars().all()
    assert len(rows) == 2
    assert rows[0].id == job.id
    assert rows[1].retry_of_job_id == job.id
