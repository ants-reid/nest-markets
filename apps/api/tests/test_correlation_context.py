"""Tests for MH-160 — correlation ID plumbing."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.correlation_context import (
    CORRELATION_HEADER,
    CorrelationIDMiddleware,
    correlation_id_var,
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)


def _app_with_middleware() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationIDMiddleware)

    @app.get("/echo")
    def echo() -> dict:
        return {"cid": get_correlation_id()}

    return app


def test_new_correlation_id_is_hex_and_unique():
    a, b = new_correlation_id(), new_correlation_id()
    assert a != b
    assert all(c in "0123456789abcdef" for c in a)


def test_set_get_reset():
    token = set_correlation_id("abc123")
    try:
        assert get_correlation_id() == "abc123"
    finally:
        correlation_id_var.reset(token)
    assert get_correlation_id() is None


def test_middleware_generates_id_when_absent():
    client = TestClient(_app_with_middleware())
    r = client.get("/echo")
    assert r.status_code == 200
    cid = r.headers.get(CORRELATION_HEADER)
    assert cid and len(cid) >= 16
    assert r.json()["cid"] == cid


def test_middleware_uses_supplied_header_when_valid():
    client = TestClient(_app_with_middleware())
    r = client.get("/echo", headers={CORRELATION_HEADER: "trace-001.abc:42"})
    assert r.headers[CORRELATION_HEADER] == "trace-001.abc:42"
    assert r.json()["cid"] == "trace-001.abc:42"


def test_middleware_rejects_malformed_header():
    client = TestClient(_app_with_middleware())
    # Contains a space => invalid by our pattern; should be replaced.
    r = client.get("/echo", headers={CORRELATION_HEADER: "bad header value"})
    cid = r.headers[CORRELATION_HEADER]
    assert cid != "bad header value"
    assert " " not in cid


def test_middleware_rejects_overlong_header():
    client = TestClient(_app_with_middleware())
    long = "a" * 500
    r = client.get("/echo", headers={CORRELATION_HEADER: long})
    cid = r.headers[CORRELATION_HEADER]
    assert cid != long
    assert len(cid) <= 100


def test_contextvar_is_reset_after_request():
    client = TestClient(_app_with_middleware())
    client.get("/echo")
    # After the request returns, the outer scope's contextvar must be unset.
    assert get_correlation_id() is None


def test_response_status_unchanged_on_4xx():
    app = _app_with_middleware()

    @app.get("/missing")
    def _missing():
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="nope")

    client = TestClient(app)
    r = client.get("/missing")
    assert r.status_code == 404
    # Header still echoed even on non-200 responses.
    assert CORRELATION_HEADER in r.headers
