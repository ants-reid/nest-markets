"""MH-149 — Sanitize untrusted text fed into LLM prompts.

Defensive cleaning applied to dict-shaped LLM inputs (e.g. ``catalyst_context``)
before they are JSON-serialized into a prompt template. The sanitizer is a
*no-op* for already-clean inputs (alphanumerics + safe punctuation under the
length cap), so existing prompts remain byte-identical for normal data.

Drift-lock notes:
    * Pure pre-rendering hardening; no trading behaviour change.
    * Does not touch enforcement, broker submit, worker execution, or risk
      evaluation paths.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Hard caps. Conservative so a malicious payload cannot blow out the prompt.
MAX_STRING_LEN: int = 8000
MAX_LIST_LEN: int = 256
MAX_DICT_KEYS: int = 256
MAX_DEPTH: int = 8

# Strip ASCII C0 (0x00–0x1F) and DEL (0x7F) except TAB (\t), LF (\n), CR (\r).
# Strip C1 controls (0x80–0x9F).
_C0_C1_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# Common "ignore previous instructions" / role-spoofing tokens. We do not
# remove them (the LLM still needs to see suspicious wording to react), but
# we collapse any embedded markdown fence that could break out of a JSON
# block in the user prompt.
_FENCE_PATTERN = re.compile(r"```+")


class LLMInputSanitizationError(ValueError):
    """Raised when an input cannot be safely sanitized (e.g. depth overflow)."""


def _sanitize_string(value: str, *, max_len: int = MAX_STRING_LEN) -> str:
    """Return a sanitized string: NFC-normalized, control-stripped, length-capped, fence-neutralized."""
    # Normalize unicode so visually-identical glyphs cannot smuggle bytes.
    normalized = unicodedata.normalize("NFC", value)
    # Strip C0/C1 control chars (keep \t \n \r).
    cleaned = _C0_C1_PATTERN.sub("", normalized)
    # Neutralize markdown code fences that could escape a quoted JSON block.
    cleaned = _FENCE_PATTERN.sub("``\u200b`", cleaned)
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "...[truncated]"
    return cleaned


def sanitize_value(value: Any, *, depth: int = 0) -> Any:
    """Recursively sanitize a JSON-compatible value.

    Strings are control-stripped + length-capped. Dicts and lists have their
    sizes capped. Primitives pass through unchanged. Unsupported types are
    coerced to their ``str()`` form and then sanitized.
    """
    if depth > MAX_DEPTH:
        raise LLMInputSanitizationError(
            f"Input nesting exceeds MAX_DEPTH={MAX_DEPTH}"
        )

    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return _sanitize_string(value)
    if isinstance(value, dict):
        items = list(value.items())
        if len(items) > MAX_DICT_KEYS:
            items = items[:MAX_DICT_KEYS]
        out: dict[str, Any] = {}
        for k, v in items:
            safe_key = _sanitize_string(str(k), max_len=256)
            out[safe_key] = sanitize_value(v, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        seq = list(value)
        if len(seq) > MAX_LIST_LEN:
            seq = seq[:MAX_LIST_LEN]
        return [sanitize_value(v, depth=depth + 1) for v in seq]
    # Fallback for unexpected types (e.g. Decimal, datetime). Coerce to str.
    return _sanitize_string(str(value))


def sanitize_dict(value: dict[str, Any]) -> dict[str, Any]:
    """Public entry point: sanitize a dict before JSON-serialization for an LLM prompt."""
    if not isinstance(value, dict):
        raise LLMInputSanitizationError("sanitize_dict expects a dict")
    return sanitize_value(value, depth=0)
