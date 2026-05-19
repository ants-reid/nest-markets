"""Cycle 44 — Schema drift-lock for ``provider_coverage_reports``.

Locks the per-provider coverage snapshot — the read-only attribution
surface for provider-priority reasoning.

Pinned shape:
  * 10 business columns + nullability + String(100) provider
  * provider indexed
  * Counter columns (total_assets, covered_assets, total_bars)
    default to 0 (drift here would silently make every provider
    look "fully covered" or "no data" without measurement)
  * ``metadata_json`` JSONB-family
  * Required identity fields (provider, evaluated_at) carry no
    silent defaults.

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

from sqlalchemy import DateTime, Float, Integer, String, Text

from app.db.models.provider_coverage_report import ProviderCoverageReport


JSON_TYPE_NAMES: frozenset[str] = frozenset({"JSONBType", "JSONB", "JSON"})


# (nullable, type, length-or-None)
EXPECTED_BUSINESS_COLUMNS: dict[str, tuple[bool, type | None, int | None]] = {
    "provider": (False, String, 100),
    "evaluated_at": (False, DateTime, None),
    "total_assets": (False, Integer, None),
    "covered_assets": (False, Integer, None),
    "coverage_pct": (True, Float, None),
    "earliest_bar_ts": (True, DateTime, None),
    "latest_bar_ts": (True, DateTime, None),
    "total_bars": (False, Integer, None),
    "notes": (True, Text, None),
    "metadata_json": (True, None, None),  # JSONB
}


COUNTERS_DEFAULT_ZERO: list[str] = ["total_assets", "covered_assets", "total_bars"]


def test_table_name_unchanged():
    assert ProviderCoverageReport.__tablename__ == "provider_coverage_reports"


def test_business_column_set_unchanged():
    table_cols = set(ProviderCoverageReport.__table__.columns.keys())
    business_cols = table_cols - {"id", "created_at"}
    expected = set(EXPECTED_BUSINESS_COLUMNS.keys())
    missing = expected - business_cols
    extra = business_cols - expected
    assert not missing, (
        f"ProviderCoverageReport missing column(s): {sorted(missing)}."
    )
    assert not extra, (
        f"ProviderCoverageReport has unexpected new column(s): {sorted(extra)}."
    )


def test_business_column_nullability_unchanged():
    for col_name, (expected_nullable, _t, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        col = ProviderCoverageReport.__table__.columns[col_name]
        assert col.nullable is expected_nullable, (
            f"ProviderCoverageReport.{col_name}.nullable changed: "
            f"expected {expected_nullable}, got {col.nullable}."
        )


def test_business_column_types_unchanged():
    for col_name, (_n, expected_type, _len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is None:
            continue
        col = ProviderCoverageReport.__table__.columns[col_name]
        assert isinstance(col.type, expected_type), (
            f"ProviderCoverageReport.{col_name} type drifted: expected "
            f"{expected_type.__name__}, got {type(col.type).__name__}."
        )


def test_string_lengths_unchanged():
    for col_name, (_n, expected_type, expected_len) in EXPECTED_BUSINESS_COLUMNS.items():
        if expected_type is not String or expected_len is None:
            continue
        col = ProviderCoverageReport.__table__.columns[col_name]
        assert isinstance(col.type, String)
        assert col.type.length == expected_len, (
            f"ProviderCoverageReport.{col_name} length drifted: "
            f"expected {expected_len}, got {col.type.length}."
        )


def test_provider_indexed():
    col = ProviderCoverageReport.__table__.columns["provider"]
    assert col.index is True, (
        "ProviderCoverageReport.provider must remain indexed."
    )


def test_metadata_json_is_jsonb_family():
    col = ProviderCoverageReport.__table__.columns["metadata_json"]
    type_name = type(col.type).__name__
    assert type_name in JSON_TYPE_NAMES, (
        f"ProviderCoverageReport.metadata_json must remain JSONB-family; "
        f"got {type_name}."
    )


def test_counters_default_to_zero():
    """Every counter column must default to 0 — drift here would let
    coverage rows silently look "fully covered" or "no data" without
    actual measurement."""
    for col_name in COUNTERS_DEFAULT_ZERO:
        col = ProviderCoverageReport.__table__.columns[col_name]
        assert col.default is not None, (
            f"ProviderCoverageReport.{col_name} lost its Python default."
        )
        assert col.default.arg == 0, (
            f"ProviderCoverageReport.{col_name} default drifted: "
            f"expected 0, got {col.default.arg!r}."
        )


def test_required_identity_fields_have_no_silent_defaults():
    for col_name in ("provider", "evaluated_at"):
        col = ProviderCoverageReport.__table__.columns[col_name]
        assert col.default is None, (
            f"ProviderCoverageReport.{col_name} gained a Python default."
        )
        assert col.server_default is None, (
            f"ProviderCoverageReport.{col_name} gained a server_default."
        )


def test_id_and_timestamps_supplied_by_mixins():
    cols = ProviderCoverageReport.__table__.columns.keys()
    assert "id" in cols
    assert "created_at" in cols
    pk_cols = [c.name for c in ProviderCoverageReport.__table__.primary_key.columns]
    assert pk_cols == ["id"]
