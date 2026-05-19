"""MH-DRIFTLOCK-APPROVAL-SERVICE-PUBLIC-API-CATALOG

Pins the public method floor of ``ApprovalService``. Removing any of these
silently would break the approval lifecycle the safety surface depends on.
"""
from __future__ import annotations

from app.services.approval_service import ApprovalService

_REQUIRED_METHODS: frozenset[str] = frozenset(
    {
        "approve",
        "approve_request",
        "create_request",
        "expire",
        "expire_request",
        "reject",
        "reject_request",
    }
)


def test_approval_service_required_methods_present() -> None:
    missing = [
        m for m in _REQUIRED_METHODS
        if not callable(getattr(ApprovalService, m, None))
    ]
    assert not missing, f"ApprovalService missing required methods: {sorted(missing)}"


def test_approval_service_method_count_floor() -> None:
    publics = [m for m in dir(ApprovalService) if not m.startswith("_") and callable(getattr(ApprovalService, m))]
    assert len(publics) >= len(_REQUIRED_METHODS), (
        f"ApprovalService public callable count regressed below floor: {len(publics)} "
        f"({sorted(publics)})"
    )
