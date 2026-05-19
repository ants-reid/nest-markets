"""MH-DRIFTLOCK-RISK-PROFILE-SERVICE-PUBLIC-API-CATALOG

Pins the public class floor of ``app.services.risk_profile_service``.
``RiskProfileService`` provides the row that drives every per-trade gate;
``RiskDefaults`` provides the default-policy snapshot.
"""
from __future__ import annotations

from app.services import risk_profile_service

_REQUIRED_CLASSES: frozenset[str] = frozenset({"RiskProfileService", "RiskDefaults"})


def test_risk_profile_service_required_exports_present() -> None:
    missing = []
    for name in _REQUIRED_CLASSES:
        obj = getattr(risk_profile_service, name, None)
        if not isinstance(obj, type):
            missing.append(name)
    assert not missing, (
        f"risk_profile_service missing required class exports: {sorted(missing)}"
    )
