"""Drift-lock: alembic revision-chain pin (cycle 71).

Pins (a) the current head revision id, (b) the unique starting
revision (down_revision is None), and (c) a migration count floor.
A second branch root (multiple heads) or a backwards rewind to an
earlier head would silently break ``alembic upgrade head`` and any
schema-pinning test based on the head id.

Test-only / additive — does NOT execute migrations.
"""

from __future__ import annotations

from pathlib import Path

EXPECTED_HEAD_REVISION = "g7h8i9j0k1l2"
EXPECTED_INITIAL_REVISION_FILE = "001_initial_tables.py"
EXPECTED_MIGRATION_COUNT_FLOOR = 31  # current 33; floor allows -2

VERSIONS_DIR = (
    Path(__file__).resolve().parents[1] / "alembic" / "versions"
)


def _migration_files() -> list[Path]:
    return sorted(p for p in VERSIONS_DIR.glob("*.py") if not p.name.startswith("__"))


def test_alembic_versions_dir_exists() -> None:
    assert VERSIONS_DIR.is_dir(), (
        f"Alembic versions directory missing at {VERSIONS_DIR}. "
        "Migration discovery would fail."
    )


def test_alembic_migration_count_floor() -> None:
    count = len(_migration_files())
    assert count >= EXPECTED_MIGRATION_COUNT_FLOOR, (
        f"Alembic migration count regressed: {count} < floor "
        f"{EXPECTED_MIGRATION_COUNT_FLOOR}."
    )


def test_alembic_initial_revision_present() -> None:
    initial = VERSIONS_DIR / EXPECTED_INITIAL_REVISION_FILE
    assert initial.exists(), (
        f"Initial migration {EXPECTED_INITIAL_REVISION_FILE!r} missing. "
        "This file's revision is the chain root; deleting it breaks "
        "every downstream upgrade."
    )
    text = initial.read_text(encoding="utf-8")
    assert "down_revision = None" in text, (
        f"{EXPECTED_INITIAL_REVISION_FILE} no longer declares "
        "down_revision = None — chain root drift."
    )


def test_alembic_head_revision_pinned() -> None:
    """Exactly one migration must declare HEAD = EXPECTED_HEAD_REVISION
    via its top-level revision = '...' string. Any drift here means
    an unannounced migration was added or an existing head was
    renamed.
    """
    target = f'revision = "{EXPECTED_HEAD_REVISION}"'
    target_alt = f"revision = '{EXPECTED_HEAD_REVISION}'"
    matches: list[str] = []
    for path in _migration_files():
        text = path.read_text(encoding="utf-8")
        if target in text or target_alt in text:
            matches.append(path.name)
    assert matches, (
        f"No migration declares revision = {EXPECTED_HEAD_REVISION!r}. "
        "Was the head revision rewritten?"
    )
    assert len(matches) == 1, (
        f"Multiple files declare the head revision "
        f"{EXPECTED_HEAD_REVISION!r}: {matches}."
    )


def test_alembic_single_chain_root() -> None:
    """At most one migration file may declare ``down_revision = None``.
    More than one would create a forked chain root that alembic
    rejects at upgrade time.
    """
    roots: list[str] = []
    for path in _migration_files():
        text = path.read_text(encoding="utf-8")
        if "down_revision = None" in text:
            roots.append(path.name)
    assert len(roots) == 1, (
        f"Alembic chain has {len(roots)} roots ({roots}); expected "
        "exactly one."
    )
