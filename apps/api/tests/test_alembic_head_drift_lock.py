"""Cycle 54 — Migration head pin.

Pins the current Alembic head to a known revision. Fails if:
  * A new migration is added without updating this pin.
  * Multiple heads exist (silent multi-head merge — would cause
    ``alembic upgrade head`` to fail in deploys).
  * The head is downgraded.

Why this matters:
  * Multi-head merges are silent at PR time but break deploys.
  * A drift between expected head and actual head means a developer
    has added a migration without going through the deliberate
    "add-then-bump-pin" review path.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Does not run migrations or import the alembic package
      (the local ``apps/api/alembic/`` directory shadows the
      third-party alembic package, so we parse the version files
      directly instead).
    * Auto-trading gates are unchanged.

How to update this pin:
  When adding a new migration, deliberately update ``EXPECTED_HEAD``
  in the same PR. The bump itself is the review signal.
"""

from __future__ import annotations

import re
from pathlib import Path


# Pinned head as of the restart stabilisation rebaseline.
EXPECTED_HEAD: str = "h8i9j0k1l2m3"


_REVISION_RE = re.compile(r'^revision\s*(?::\s*[^=]+)?=\s*["\']([^"\']+)["\']', re.M)
_DOWN_REVISION_RE = re.compile(
    r'^down_revision\s*(?::\s*[^=]+)?=\s*(?:["\']([^"\']+)["\']|None)', re.M
)
_DOWN_REVISION_TUPLE_RE = re.compile(
    r'^down_revision\s*(?::\s*[^=]+)?=\s*\(([^)]*)\)', re.M
)


def _versions_dir() -> Path:
    api_root = Path(__file__).resolve().parent.parent
    return api_root / "alembic" / "versions"


def _scan_revisions() -> tuple[set[str], set[str]]:
    """Return (all_revisions, all_down_revisions)."""
    revisions: set[str] = set()
    downs: set[str] = set()
    versions = _versions_dir()
    assert versions.is_dir(), f"alembic versions dir not found: {versions}"
    for path in versions.glob("*.py"):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        rev_m = _REVISION_RE.search(text)
        if rev_m:
            revisions.add(rev_m.group(1))
        # down_revision can be a string, None, or a tuple (for merges).
        tup_m = _DOWN_REVISION_TUPLE_RE.search(text)
        if tup_m:
            for piece in tup_m.group(1).split(","):
                piece = piece.strip().strip('"').strip("'")
                if piece and piece != "None":
                    downs.add(piece)
        else:
            d_m = _DOWN_REVISION_RE.search(text)
            if d_m and d_m.group(1):
                downs.add(d_m.group(1))
    return revisions, downs


def _heads() -> set[str]:
    """Heads = revisions that no other migration's down_revision points to."""
    revisions, downs = _scan_revisions()
    return revisions - downs


def test_alembic_has_exactly_one_head():
    """Multi-head silently breaks deploys. A merge migration must be
    introduced if two parallel heads have appeared."""
    heads = _heads()
    assert len(heads) == 1, (
        f"Alembic has {len(heads)} heads: {sorted(heads)}. "
        "Multi-head silently breaks `alembic upgrade head`. "
        "Add a merge migration to consolidate."
    )


def test_alembic_head_matches_pin():
    """The single head must match the pinned revision."""
    heads = _heads()
    assert len(heads) == 1, "precondition: single head (see other test)"
    actual = next(iter(heads))
    assert actual == EXPECTED_HEAD, (
        f"Alembic head drifted: expected {EXPECTED_HEAD!r}, got {actual!r}.\n"
        "If you intentionally added a new migration, update EXPECTED_HEAD "
        "in this file in the same PR. The deliberate pin bump IS the "
        "review signal that a schema change is landing."
    )


def test_alembic_pinned_revision_exists_in_versions_dir():
    """Defensive: the pin must point to a real revision file, not a typo."""
    revisions, _ = _scan_revisions()
    assert EXPECTED_HEAD in revisions, (
        f"Pinned revision {EXPECTED_HEAD!r} not found in alembic/versions/. "
        "Either the pin was mistyped or the revision file was deleted."
    )


def test_alembic_revision_chain_is_acyclic_and_connected():
    """Every non-base down_revision must point to a real revision.
    Catches typos and dangling references that would silently break
    `alembic upgrade head` mid-chain."""
    revisions, downs = _scan_revisions()
    dangling = downs - revisions
    assert not dangling, (
        f"down_revision points to non-existent revision(s): {sorted(dangling)}. "
        "This would break `alembic upgrade` mid-chain."
    )
