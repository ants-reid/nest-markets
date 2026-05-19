"""Drift-lock: OpenAPI safety-component catalog (cycle 70).

Pins the FLOOR for the number of generated OpenAPI schema components
and confirms the safety-relevant request/response components are
present. A regression that drops one of these would break OpenAPI
clients of the trading paths even though service code still works.

Test-only / additive.
"""

from __future__ import annotations

from app.main import create_app

# Floor (not exact). The current count is 218; we allow growth but
# guard against accidental mass-removal.
EXPECTED_SCHEMA_FLOOR = 200

SAFETY_REQUIRED_SCHEMAS: frozenset[str] = frozenset(
    {
        "PaperExecutionResponse",
        "LiveExecutionResponse",
        "WorkflowRunResponse",
        "HTTPValidationError",
    }
)


def _components_schemas() -> dict:
    app = create_app()
    spec = app.openapi()
    return (spec.get("components") or {}).get("schemas", {}) or {}


def test_openapi_schema_count_floor() -> None:
    schemas = _components_schemas()
    count = len(schemas)
    assert count >= EXPECTED_SCHEMA_FLOOR, (
        f"OpenAPI schema-component count regression: {count} < floor "
        f"{EXPECTED_SCHEMA_FLOOR}. Investigate which routers/models "
        "stopped registering."
    )


def test_openapi_safety_components_present() -> None:
    schemas = _components_schemas()
    missing = SAFETY_REQUIRED_SCHEMAS - frozenset(schemas.keys())
    assert not missing, (
        f"OpenAPI is missing safety-required component(s): "
        f"{sorted(missing)}. These are the contracts the paper and "
        "live execution endpoints expose; their absence breaks every "
        "OpenAPI client even if the route still functions."
    )
