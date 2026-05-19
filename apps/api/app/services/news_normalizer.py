"""MH-NEWS-02 — News normalized JSON schema + storage helpers.

Converts a raw Perplexity / Sonar response (or any provider that follows the
same shape) into a structured ``NormalizedNewsArticle`` ready for storage in
``news_articles``. Also exposes a small builder that maps a normalized
article into the ORM row (without committing) for callers that opt in.

DRIFT-LOCK GUARANTEE
--------------------
- This module is **research-only**. It never imports broker, worker,
  scheduler, signal-engine, or risk-evaluator code.
- It never relaxes a risk control. The MH-NEWS-04 risk advisory and the
  MH-NEWS-06 ``evidence_class='research_only'`` DB-CHECK constraint will be
  enforced in their own future phases; this module is consumption-only.
- ``raw_json`` is preserved verbatim alongside the normalized fields so
  downstream auditors can re-derive the normalization deterministically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Iterable, Optional, Sequence

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
_MAX_HEADLINE_LEN = 500
_MAX_SUMMARY_LEN = 4000
_MAX_BODY_LEN = 50_000
_MAX_URL_LEN = 1000


class NewsNormalizationError(ValueError):
    """Raised when an item cannot be normalized into a valid article."""


@dataclass(frozen=True)
class NormalizedCitation:
    url: str
    title: Optional[str] = None
    published_at: Optional[datetime] = None


@dataclass(frozen=True)
class NormalizedNewsArticle:
    external_id: Optional[str]
    headline: str
    summary: Optional[str]
    body_text: Optional[str]
    source: Optional[str]
    url: Optional[str]
    published_at: Optional[datetime]
    tickers: tuple[str, ...] = field(default_factory=tuple)
    authors: tuple[str, ...] = field(default_factory=tuple)
    sector_tags: tuple[str, ...] = field(default_factory=tuple)
    citations: tuple[NormalizedCitation, ...] = field(default_factory=tuple)
    raw: dict[str, Any] = field(default_factory=dict)
    # Always 'research_only'; MH-NEWS-06 will enforce this with a DB CHECK.
    evidence_class: str = "research_only"


def _coerce_str(value: Any, *, max_len: Optional[int] = None) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return None
    if max_len is not None and len(value) > max_len:
        value = value[: max_len - 1] + "…"
    return value


def _coerce_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Tolerate trailing 'Z' (Python <3.11 stricter) and missing tz.
        s = s.replace("Z", "+00:00") if s.endswith("Z") else s
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    return None


def _coerce_tickers(values: Any) -> tuple[str, ...]:
    if not values:
        return ()
    if isinstance(values, str):
        candidates: Iterable[str] = re.split(r"[,\s]+", values)
    elif isinstance(values, Iterable):
        candidates = (str(v) for v in values)
    else:
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        norm = raw.strip().upper()
        if not norm or norm in seen:
            continue
        if not _TICKER_RE.match(norm):
            continue
        seen.add(norm)
        out.append(norm)
    return tuple(out)


def _coerce_str_list(values: Any, *, max_items: int = 50) -> tuple[str, ...]:
    if not values:
        return ()
    if isinstance(values, str):
        items: Iterable = [values]
    elif isinstance(values, Iterable):
        items = values
    else:
        return ()
    out: list[str] = []
    for item in items:
        s = _coerce_str(item, max_len=200)
        if s and s not in out:
            out.append(s)
        if len(out) >= max_items:
            break
    return tuple(out)


def _coerce_citation(item: Any) -> Optional[NormalizedCitation]:
    if item is None:
        return None
    if isinstance(item, str):
        url = _coerce_str(item, max_len=_MAX_URL_LEN)
        return NormalizedCitation(url=url) if url else None
    if isinstance(item, dict):
        url = _coerce_str(item.get("url"), max_len=_MAX_URL_LEN)
        if not url:
            return None
        return NormalizedCitation(
            url=url,
            title=_coerce_str(item.get("title"), max_len=_MAX_HEADLINE_LEN),
            published_at=_coerce_datetime(item.get("published_at")),
        )
    return None


def normalize_news_item(
    item: dict[str, Any],
    *,
    citations: Sequence[Any] = (),
) -> NormalizedNewsArticle:
    """Normalize one provider-shaped dict into a ``NormalizedNewsArticle``.

    Required field: ``headline`` (non-empty after stripping). Everything else
    is best-effort. Raises ``NewsNormalizationError`` if the headline is
    missing — we refuse to store an article with no human-readable label.
    """
    if not isinstance(item, dict):
        raise NewsNormalizationError(f"item must be dict, got {type(item).__name__}")
    headline = _coerce_str(item.get("headline") or item.get("title"), max_len=_MAX_HEADLINE_LEN)
    if not headline:
        raise NewsNormalizationError("news item missing headline")

    cit_iter = list(citations or []) + list(item.get("citations") or [])
    norm_citations = tuple(c for c in (_coerce_citation(x) for x in cit_iter) if c is not None)

    return NormalizedNewsArticle(
        external_id=_coerce_str(item.get("external_id") or item.get("id"), max_len=255),
        headline=headline,
        summary=_coerce_str(item.get("summary"), max_len=_MAX_SUMMARY_LEN),
        body_text=_coerce_str(item.get("body_text") or item.get("content"), max_len=_MAX_BODY_LEN),
        source=_coerce_str(item.get("source") or item.get("source_name"), max_len=255),
        url=_coerce_str(item.get("url"), max_len=_MAX_URL_LEN),
        published_at=_coerce_datetime(item.get("published_at") or item.get("date")),
        tickers=_coerce_tickers(item.get("tickers") or item.get("symbols")),
        authors=_coerce_str_list(item.get("authors")),
        sector_tags=_coerce_str_list(item.get("sector_tags") or item.get("sectors")),
        citations=norm_citations,
        raw=dict(item),
    )


def normalize_perplexity_response(
    response: Any,
    *,
    requested_symbols: Optional[Sequence[str]] = None,
) -> tuple[NormalizedNewsArticle, ...]:
    """Normalize a Sonar-style response into a tuple of normalized articles.

    Accepts either:
    - a raw dict shaped like ``{"items": [...], "citations": [...]}``
    - the OpenAI-style ``chat/completions`` envelope, where the JSON payload
      is in ``choices[0].message.content`` (string).

    Unknown shapes return an empty tuple rather than raising — callers that
    need strictness should validate themselves.
    """
    payload = _extract_payload(response)
    if not isinstance(payload, dict):
        return ()
    items = payload.get("items") or []
    if not isinstance(items, list):
        return ()
    shared_citations = payload.get("citations") or []
    out: list[NormalizedNewsArticle] = []
    for raw_item in items:
        try:
            article = normalize_news_item(raw_item, citations=shared_citations)
        except NewsNormalizationError:
            continue
        # Soft filter: if caller asked about specific symbols and the article
        # has *no* tickers, keep it (the caller asked broadly). If the article
        # has tickers but none overlap, drop it.
        if requested_symbols and article.tickers:
            wanted = {s.upper() for s in requested_symbols}
            if not (set(article.tickers) & wanted):
                continue
        out.append(article)
    return tuple(out)


def _extract_payload(response: Any) -> Any:
    """Pull the JSON payload out of either a plain dict or an OpenAI envelope."""
    if response is None:
        return None
    if isinstance(response, dict):
        # OpenAI/Sonar chat envelope?
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            content = (choices[0] or {}).get("message", {}).get("content")
            if isinstance(content, dict):
                return content
            if isinstance(content, str):
                import json

                try:
                    return json.loads(content)
                except (ValueError, TypeError):
                    return None
        return response
    # An object with a `.json()` method (httpx.Response style).
    json_method = getattr(response, "json", None)
    if callable(json_method):
        try:
            return _extract_payload(json_method())
        except Exception:  # noqa: BLE001
            return None
    return None


__all__ = [
    "NewsNormalizationError",
    "NormalizedCitation",
    "NormalizedNewsArticle",
    "normalize_news_item",
    "normalize_perplexity_response",
]
