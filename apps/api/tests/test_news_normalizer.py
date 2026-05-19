"""Tests for MH-NEWS-02 — news normalizer."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.services.news_normalizer import (
    NewsNormalizationError,
    NormalizedNewsArticle,
    normalize_news_item,
    normalize_perplexity_response,
)


def test_normalize_minimal_item():
    art = normalize_news_item({"headline": "Hello"})
    assert isinstance(art, NormalizedNewsArticle)
    assert art.headline == "Hello"
    assert art.evidence_class == "research_only"
    assert art.tickers == ()
    assert art.citations == ()
    assert art.raw == {"headline": "Hello"}


def test_normalize_rejects_missing_headline():
    with pytest.raises(NewsNormalizationError):
        normalize_news_item({"summary": "no headline"})
    with pytest.raises(NewsNormalizationError):
        normalize_news_item({"headline": "   "})


def test_normalize_rejects_non_dict():
    with pytest.raises(NewsNormalizationError):
        normalize_news_item("not a dict")  # type: ignore[arg-type]


def test_tickers_are_validated_and_uppercased():
    art = normalize_news_item(
        {"headline": "h", "tickers": ["aapl", "MSFT", "bad ticker", "GOOG", "AAPL"]}
    )
    # Order preserved; duplicates removed; invalid dropped.
    assert art.tickers == ("AAPL", "MSFT", "GOOG")


def test_tickers_string_is_split():
    art = normalize_news_item({"headline": "h", "tickers": "AAPL, MSFT TSLA"})
    assert art.tickers == ("AAPL", "MSFT", "TSLA")


def test_published_at_parses_iso_z():
    art = normalize_news_item({"headline": "h", "published_at": "2026-05-02T12:00:00Z"})
    assert art.published_at == datetime(2026, 5, 2, 12, 0, tzinfo=UTC)


def test_published_at_parses_unix():
    art = normalize_news_item({"headline": "h", "published_at": 1735689600})
    assert art.published_at is not None
    assert art.published_at.tzinfo is not None


def test_published_at_invalid_returns_none():
    art = normalize_news_item({"headline": "h", "published_at": "not a date"})
    assert art.published_at is None


def test_long_fields_are_truncated():
    art = normalize_news_item({"headline": "x" * 1000})
    assert len(art.headline) <= 500


def test_citations_dict_and_string_forms():
    art = normalize_news_item(
        {
            "headline": "h",
            "citations": [
                "https://example.com/a",
                {"url": "https://example.com/b", "title": "Source B"},
                {"no_url": True},  # dropped
                None,  # dropped
            ],
        }
    )
    urls = [c.url for c in art.citations]
    assert urls == ["https://example.com/a", "https://example.com/b"]
    assert art.citations[1].title == "Source B"


def test_normalize_perplexity_dict_response():
    resp = {
        "items": [
            {"headline": "A", "tickers": ["AAPL"]},
            {"headline": "B", "tickers": ["MSFT"]},
            {"summary": "no headline, dropped"},
        ],
        "citations": [{"url": "https://e.example/1"}],
    }
    out = normalize_perplexity_response(resp)
    assert len(out) == 2
    # Shared citations attached to both items.
    assert all(a.citations and a.citations[0].url == "https://e.example/1" for a in out)


def test_normalize_perplexity_filters_by_requested_symbols():
    resp = {
        "items": [
            {"headline": "A", "tickers": ["AAPL"]},
            {"headline": "B", "tickers": ["MSFT"]},
            {"headline": "C"},  # no tickers — kept (broad ask)
        ]
    }
    out = normalize_perplexity_response(resp, requested_symbols=["AAPL"])
    headlines = [a.headline for a in out]
    assert "A" in headlines
    assert "B" not in headlines
    assert "C" in headlines


def test_normalize_perplexity_openai_envelope():
    resp = {
        "choices": [
            {
                "message": {
                    "content": '{"items": [{"headline": "Z"}], "citations": []}'
                }
            }
        ]
    }
    out = normalize_perplexity_response(resp)
    assert len(out) == 1
    assert out[0].headline == "Z"


def test_normalize_perplexity_handles_garbage():
    assert normalize_perplexity_response(None) == ()
    assert normalize_perplexity_response("string") == ()
    assert normalize_perplexity_response({"items": "not a list"}) == ()
    assert normalize_perplexity_response({"choices": [{"message": {"content": "not json"}}]}) == ()


def test_evidence_class_is_research_only_by_default():
    art = normalize_news_item({"headline": "h"})
    assert art.evidence_class == "research_only"
