"""MH-159 — Prompt registry with frontmatter parsing + content hash.

Loads prompt templates from `apps/api/app/prompts/**/*.md`, parses a small
comment-style frontmatter (lines beginning with ``# key: value`` at the top
of the file followed by a blank line), and exposes each prompt as a
``PromptDescriptor`` with:

* ``name`` / ``role`` / ``version`` / ``schema`` — frontmatter fields
* ``body`` — the prompt text below the frontmatter (or the whole file if no
  frontmatter is present)
* ``content_hash`` — sha256 hex of the body bytes (stable across runs)
* ``version_id`` — UUID v5 derived from ``(name, version, content_hash)``

The ``version_id`` is the value future LLM call sites will write into the
``LLMRequestLog.prompt_version_id`` column so each row is bound to an exact
prompt revision.

DRIFT-LOCK GUARANTEE
--------------------
This module is pure and read-only. It does NOT:

* call any LLM provider
* mutate any prompt file
* import the broker, worker, or trading-control modules
* change the behaviour of any existing call site

It only ships the *producer* contract; wiring into ``OpenAIProvider``
remains deferred to a future MH-AI-* phase per the matrix.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

# Stable namespace for prompt version_ids. Hard-coded so re-deploys produce
# the same UUID for the same (name, version, content_hash) triple.
_PROMPT_NS = uuid.UUID("4f3c9b6a-1f57-4f3a-b7d3-9c2e1d4f9a6e")

_FRONTMATTER_LINE = re.compile(r"^#\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$")


class PromptRegistryError(ValueError):
    """Raised on registry consistency / lookup failures."""


@dataclass(frozen=True)
class PromptDescriptor:
    name: str
    role: str
    version: str
    schema: Optional[str]
    body: str
    content_hash: str
    version_id: uuid.UUID
    source_path: str
    extra: Dict[str, str] = field(default_factory=dict)


def _parse_frontmatter(text: str) -> tuple[Dict[str, str], str]:
    """Return ``(metadata, body)`` from a prompt file.

    Frontmatter format: contiguous block of ``# key: value`` lines starting at
    line 1, terminated by a blank line. Anything after that blank line is the
    body. If line 1 is not a frontmatter line, the entire file is treated as
    body and metadata is empty.
    """
    lines = text.splitlines(keepends=False)
    meta: Dict[str, str] = {}
    body_start = 0
    if not lines or not _FRONTMATTER_LINE.match(lines[0] or ""):
        return meta, text
    for i, line in enumerate(lines):
        if line.strip() == "":
            body_start = i + 1
            break
        m = _FRONTMATTER_LINE.match(line)
        if not m:
            # First non-frontmatter, non-blank line — treat from here as body.
            body_start = i
            break
        key, value = m.group(1).lower(), m.group(2)
        meta[key] = value
    else:
        # File was *only* frontmatter, no blank line, no body.
        body_start = len(lines)
    body = "\n".join(lines[body_start:])
    # Preserve trailing newline iff the original had one and there is body.
    if body and text.endswith("\n") and not body.endswith("\n"):
        body += "\n"
    return meta, body


def _hash_body(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest()


def _version_id(name: str, version: str, content_hash: str) -> uuid.UUID:
    return uuid.uuid5(_PROMPT_NS, f"{name}|{version}|{content_hash}")


def describe_prompt_text(text: str, *, source_path: str = "<memory>") -> PromptDescriptor:
    """Parse one in-memory prompt string into a ``PromptDescriptor``.

    Required frontmatter fields: ``name``, ``role``, ``version``. Missing
    fields raise ``PromptRegistryError`` so prompt provenance is never
    silently empty in production.
    """
    meta, body = _parse_frontmatter(text)
    missing = [k for k in ("name", "role", "version") if not meta.get(k)]
    if missing:
        raise PromptRegistryError(
            f"prompt at {source_path} is missing required frontmatter fields: {missing}"
        )
    h = _hash_body(body)
    return PromptDescriptor(
        name=meta["name"],
        role=meta["role"],
        version=meta["version"],
        schema=meta.get("schema"),
        body=body,
        content_hash=h,
        version_id=_version_id(meta["name"], meta["version"], h),
        source_path=source_path,
        extra={k: v for k, v in meta.items() if k not in {"name", "role", "version", "schema"}},
    )


def load_prompt_file(path: Path) -> PromptDescriptor:
    """Load and parse a single ``.md`` prompt file."""
    text = path.read_text(encoding="utf-8")
    return describe_prompt_text(text, source_path=str(path))


def load_prompt_directory(root: Path) -> Dict[str, PromptDescriptor]:
    """Recursively load every ``*.md`` under ``root``.

    Returns a dict keyed by ``"{role}/{name}@{version}"``. Raises
    ``PromptRegistryError`` if two files would collide on the same key
    (which would mean two different files claim to be the same prompt
    revision — that is a real bug, not a soft warning).
    """
    if not root.exists():
        raise PromptRegistryError(f"prompt root does not exist: {root}")
    out: Dict[str, PromptDescriptor] = {}
    for path in sorted(root.rglob("*.md")):
        # Skip files with no frontmatter at all (e.g. user-input templates).
        text = path.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(text)
        if not meta.get("name") or not meta.get("version"):
            continue
        desc = describe_prompt_text(text, source_path=str(path))
        key = f"{desc.role}/{desc.name}@{desc.version}"
        if key in out and out[key].content_hash != desc.content_hash:
            raise PromptRegistryError(
                f"prompt key collision: {key} at {path} differs from {out[key].source_path}"
            )
        out[key] = desc
    return out
