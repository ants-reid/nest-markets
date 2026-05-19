"""Drift-lock: CORS allowed-origins default catalog (cycle 66).

Pins ``Settings.cors_allowed_origins`` field default to the exact
two-entry localhost list. A silent change to ``["*"]`` (or any wildcard)
would let arbitrary browser origins call trading endpoints with a
captured API key; we hard-block that here.

Test-only / additive.
"""

from __future__ import annotations

from app.config import Settings

EXPECTED_CORS_DEFAULT: tuple[str, ...] = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)

FORBIDDEN_CORS_VALUES: frozenset[str] = frozenset({"*", "null"})


def _field_default() -> list[str]:
    field = Settings.model_fields["cors_allowed_origins"]
    default = field.default
    # pydantic stores list defaults as the list directly; defensive copy.
    return list(default) if default is not None else []


def test_cors_default_value_unchanged() -> None:
    actual = tuple(_field_default())
    assert actual == EXPECTED_CORS_DEFAULT, (
        "Settings.cors_allowed_origins default drift detected.\n"
        f"  expected: {EXPECTED_CORS_DEFAULT}\n"
        f"  actual:   {actual}\n"
        "If intentional, update EXPECTED_CORS_DEFAULT and confirm no "
        "wildcard origin was introduced."
    )


def test_cors_default_has_no_wildcard() -> None:
    actual = _field_default()
    bad = [o for o in actual if o in FORBIDDEN_CORS_VALUES]
    assert not bad, (
        f"Wildcard / null CORS origin in Settings default: {bad}. "
        "This would let any browser origin invoke trading endpoints "
        "with a leaked API key."
    )


def test_cors_default_uses_localhost_only() -> None:
    actual = _field_default()
    for origin in actual:
        assert "localhost" in origin or "127.0.0.1" in origin, (
            f"Non-local default CORS origin {origin!r} found in "
            "Settings. Production origins must be supplied via env, "
            "not baked into defaults."
        )
