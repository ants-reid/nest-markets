"""MH-NEWS-01 — Perplexity / Sonar news provider adapter.

Adds a thin ``NewsAdapter`` implementation for the Perplexity Sonar API. The
adapter is intentionally **off by default** — nothing in production
constructs it unless a downstream phase explicitly wires it. This keeps
MH-NEWS-01 a pure additive scaffold.

DRIFT-LOCK GUARANTEE
--------------------
- This module is **not** imported by any worker, scheduler, risk evaluator,
  signal pipeline, or broker path.
- Output is research-only; the matching DB-CHECK constraint
  (``evidence_class='research_only'``) ships in MH-NEWS-06.
- The adapter never reads or modifies any trading table.
- Network calls are made only when ``fetch_news`` is invoked **and** an
  HTTP client is supplied; the default constructor produces an inert
  instance suitable for tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable, Optional, Protocol, Sequence

from app.clients.news.base import NewsAdapter, NewsRecord

logger = logging.getLogger(__name__)


class _AsyncHTTPClient(Protocol):
    """Minimal async HTTP client surface (subset of ``httpx.AsyncClient``)."""

    async def post(self, url: str, *, json: dict, headers: dict) -> Any:  # pragma: no cover
        ...


@dataclass(frozen=True)
class PerplexityCitation:
    """One supporting citation as returned by Sonar."""

    url: str
    title: Optional[str] = None
    published_at: Optional[datetime] = None


@dataclass(frozen=True)
class PerplexityNewsRecord(NewsRecord):
    """Sonar-specific record carrying the citation list verbatim."""

    citations: tuple[PerplexityCitation, ...] = ()


class PerplexityNewsAdapter(NewsAdapter):
    """Sonar-backed news adapter.

    Parameters
    ----------
    api_key:
        Perplexity API key. If empty, ``fetch_news`` raises ``RuntimeError``.
    http_client:
        Optional injected async client (matches a subset of ``httpx.AsyncClient``).
        If ``None`` and ``fetch_news`` is called, a ``RuntimeError`` is raised
        — we deliberately do not auto-construct a network client to keep this
        module side-effect-free at import time.
    model:
        Sonar model name (default ``"sonar-small-online"``).
    base_url:
        Override for the API base URL.
    """

    _DEFAULT_BASE_URL = "https://api.perplexity.ai"

    def __init__(
        self,
        *,
        api_key: str = "",
        http_client: Optional[_AsyncHTTPClient] = None,
        model: str = "sonar-small-online",
        base_url: Optional[str] = None,
    ) -> None:
        self._api_key = api_key
        self._http_client = http_client
        self._model = model
        self._base_url = base_url or self._DEFAULT_BASE_URL

    @property
    def provider_name(self) -> str:
        return "perplexity_sonar"

    async def fetch_news(
        self,
        symbols: Sequence[str] | None = None,
        *,
        limit: int = 50,
    ) -> Sequence[NewsRecord]:
        if not self._api_key:
            raise RuntimeError("PerplexityNewsAdapter: api_key is required to fetch news")
        if self._http_client is None:
            raise RuntimeError(
                "PerplexityNewsAdapter: no http_client injected; "
                "construct with http_client=httpx.AsyncClient() at call site"
            )
        prompt = _build_prompt(symbols=symbols, limit=limit)
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "return_citations": True,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        response = await self._http_client.post(
            f"{self._base_url}/chat/completions", json=payload, headers=headers
        )
        # The provider ABC promises a Sequence[NewsRecord]. We delegate parsing
        # to the normalizer so this adapter stays a thin transport layer.
        from app.services.news_normalizer import normalize_perplexity_response

        normalized = normalize_perplexity_response(response, requested_symbols=symbols)
        return tuple(_to_news_record(item) for item in normalized)

    async def health_check(self) -> bool:
        """Return True only if both an API key and an HTTP client are present.

        We do NOT issue a network probe here — that would couple
        ``/health/services`` to a paid third-party endpoint. MH-MON-02
        already classifies this as a config-only probe.
        """
        return bool(self._api_key) and self._http_client is not None


def _build_prompt(*, symbols: Sequence[str] | None, limit: int) -> str:
    sym_clause = (
        f" focused on the following tickers: {', '.join(symbols)}." if symbols else ""
    )
    return (
        f"List up to {limit} recent market-moving news items{sym_clause} "
        "Return JSON with fields: items (array of "
        "{external_id, headline, summary, source, url, published_at, tickers}), "
        "citations (array of {url, title, published_at})."
    )


def _to_news_record(normalized) -> PerplexityNewsRecord:
    return PerplexityNewsRecord(
        external_id=normalized.external_id,
        headline=normalized.headline,
        source=normalized.source or "perplexity_sonar",
        published_at=normalized.published_at or datetime.now(UTC),
        summary=normalized.summary,
        url=normalized.url,
        tickers=tuple(normalized.tickers),
        sentiment_score=None,
        citations=tuple(
            PerplexityCitation(
                url=c.url,
                title=c.title,
                published_at=c.published_at,
            )
            for c in (normalized.citations or ())
        ),
    )


__all__ = [
    "PerplexityCitation",
    "PerplexityNewsAdapter",
    "PerplexityNewsRecord",
]


# Re-exports needed only when the optional normalizer is *not* loaded yet
# (avoids hard import cycle in unit tests that load this module first).
def _safe_iterable(x: Iterable | None) -> Iterable:
    return x or ()
