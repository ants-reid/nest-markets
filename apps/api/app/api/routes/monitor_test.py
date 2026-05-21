"""MH-MON-10 — Operator-triggered dry-probe endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.middleware.auth import api_key_auth
from app.schemas.monitor_test import MonitorDryProbeResponseSchema
from app.services.monitor_test_service import (
    MonitorDryProbeCooldownError,
    MonitorDryProbeError,
    MonitorDryProbeUnsupportedError,
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
    except MonitorDryProbeCooldownError as exc:
        return JSONResponse(
            status_code=429,
            content={
                "detail": str(exc),
                "service_id": exc.service_id,
                "retry_after_seconds": round(exc.retry_after_seconds, 2),
                "dry_probe": True,
            },
            headers={"Retry-After": str(max(1, int(exc.retry_after_seconds)))}
        )
    except MonitorDryProbeUnsupportedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MonitorDryProbeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
