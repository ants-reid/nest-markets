"""MH-MON-10 — Operator-triggered dry-probe endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.middleware.auth import api_key_auth
from app.schemas.monitor_test import MonitorDryProbeResponseSchema
from app.services.monitor_test_service import (
    MonitorDryProbeError,
    run_operator_dry_probe,
)

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.post("/test/{service_id}", response_model=MonitorDryProbeResponseSchema)
def run_monitor_dry_probe(
    service_id: str,
    _: Annotated[str, Depends(api_key_auth)] = None,
) -> MonitorDryProbeResponseSchema:
    """Run a safe, read-only dry probe for one known monitor service.

    Auth is enforced via ``api_key_auth`` when ``API_KEY`` is configured.
    In development with no API key configured, auth is pass-through by design.
    """
    try:
        return run_operator_dry_probe(service_id)
    except MonitorDryProbeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
