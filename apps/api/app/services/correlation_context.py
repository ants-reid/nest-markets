"""MH-160 — Correlation ID plumbing.

Provides a single shared correlation id per inbound HTTP request so future
LLM round-trip rows, audit decisions, and log lines can all be joined to
the same trace.

Surface:

* ``correlation_id_var``           — ``ContextVar[Optional[str]]``
* ``get_correlation_id()``         — read current value (may be ``None``)
* ``set_correlation_id(value)``    — set explicitly (returns the token to reset with)
* ``new_correlation_id()``         — generate a fresh URL-safe id
* ``CorrelationIDMiddleware``      — Starlette middleware that:
    - reads ``X-Correlation-ID`` from the request (if well-formed),
    - else generates a new one,
    - binds it to the contextvar for the request scope,
    - echoes it back as ``X-Correlation-ID`` on the response.

DRIFT-LOCK GUARANTEE
--------------------
The middleware is **purely passive**:

* never short-circuits a request
* never alters status codes
* never reads or writes request bodies
* never imports broker / worker / trading-control modules
* never logs prompt content

If the middleware itself raises (it should not), the error propagates
through the normal Starlette path; the contextvar is always reset in a
``finally`` block so request leakage is impossible.
"""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

CORRELATION_HEADER = "X-Correlation-ID"
_MAX_HEADER_LEN = 100
# Accept only conservative ASCII to prevent header-injection / log-injection.
_VALID_PATTERN = re.compile(r"^[A-Za-z0-9_.:\-]{1,100}$")

correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "market_hunter_correlation_id", default=None
)


def get_correlation_id() -> Optional[str]:
    return correlation_id_var.get()


def set_correlation_id(value: Optional[str]):
    """Set the current correlation id. Returns the contextvar reset token."""
    return correlation_id_var.set(value)


def reset_correlation_id(token) -> None:
    correlation_id_var.reset(token)


def new_correlation_id() -> str:
    """Generate a fresh URL-safe correlation id (uuid4 hex)."""
    return uuid.uuid4().hex


def _coerce_header(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw = raw.strip()
    if not raw or len(raw) > _MAX_HEADER_LEN:
        return None
    if not _VALID_PATTERN.match(raw):
        return None
    return raw


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Bind a correlation id to the request scope and echo it on the response."""

    def __init__(self, app: ASGIApp, header_name: str = CORRELATION_HEADER) -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = _coerce_header(request.headers.get(self.header_name))
        cid = incoming or new_correlation_id()
        token = correlation_id_var.set(cid)
        try:
            response = await call_next(request)
        finally:
            correlation_id_var.reset(token)
        # Always echo (even if upstream-supplied) so callers can correlate.
        response.headers[self.header_name] = cid
        return response
