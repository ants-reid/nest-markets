"""MH-MON-07 — Provider Inventory tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.services.health_registry import (
    ProbeResult,
    register_probe,
    unregister_probe,
)
from app.services.provider_inventory_service import (
    list_provider_inventory,
    provider_inventory_response,
)


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def _temp_probe():
    name = "feeds_in.unit_test_provider"

    def _probe() -> ProbeResult:
        return ProbeResult(
            status="ok",
            detail="unit-test provider configured",
            extra={"configured": True, "api_key": "should-be-redacted"},
        )

    register_probe(name, _probe)
    yield name
    unregister_probe(name)


def test_classification_by_name_prefix(_temp_probe):
    rows = list_provider_inventory()
    by_name = {r.name: r for r in rows}
    assert by_name[_temp_probe].category == "feeds_in"


def test_secret_keys_are_scrubbed(_temp_probe):
    rows = list_provider_inventory()
    row = next(r for r in rows if r.name == _temp_probe)
    assert "api_key" not in row.extra
    assert row.configured is True


def test_configured_falls_back_to_status_ok():
    name = "feeds_out.unit_test_no_extra"

    def _probe() -> ProbeResult:
        return ProbeResult(status="ok", detail="ok no extra")

    register_probe(name, _probe)
    try:
        rows = list_provider_inventory()
        row = next(r for r in rows if r.name == name)
        assert row.configured is True
        assert row.category == "feeds_out"
    finally:
        unregister_probe(name)


def test_infrastructure_classification():
    rows = list_provider_inventory()
    db_row = next((r for r in rows if r.name == "database"), None)
    assert db_row is not None
    assert db_row.category == "infrastructure"


def test_endpoint_payload_shape(client, _temp_probe):
    resp = client.get("/health/providers")
    assert resp.status_code == 200
    body = resp.json()
    assert "providers" in body
    assert "totals" in body
    totals = body["totals"]
    assert totals["count"] == len(body["providers"])
    assert isinstance(totals["by_category"], dict)
    assert isinstance(totals["configured_by_category"], dict)
    # The temp probe must be present and scrubbed in the wire payload.
    found = next((p for p in body["providers"] if p["name"] == _temp_probe), None)
    assert found is not None
    assert "api_key" not in found.get("extra", {})


def test_aggregate_counts_match_rows(client):
    resp = client.get("/health/providers")
    body = resp.json()
    rows = body["providers"]
    expected_by_cat: dict[str, int] = {}
    expected_configured: dict[str, int] = {}
    for r in rows:
        expected_by_cat[r["category"]] = expected_by_cat.get(r["category"], 0) + 1
        if r["configured"]:
            expected_configured[r["category"]] = (
                expected_configured.get(r["category"], 0) + 1
            )
    assert body["totals"]["by_category"] == expected_by_cat
    assert body["totals"]["configured_by_category"] == expected_configured


def test_response_is_idempotent_within_call(client):
    """Two consecutive calls return the same provider names + categories."""
    a = client.get("/health/providers").json()
    b = client.get("/health/providers").json()
    names_a = sorted([p["name"] for p in a["providers"]])
    names_b = sorted([p["name"] for p in b["providers"]])
    assert names_a == names_b


def test_endpoint_dict_helper_matches_endpoint(client):
    direct = provider_inventory_response()
    via_http = client.get("/health/providers").json()
    # Same set of provider names; status/checked_at vary per call so don't compare those.
    assert sorted(p["name"] for p in direct["providers"]) == sorted(
        p["name"] for p in via_http["providers"]
    )
