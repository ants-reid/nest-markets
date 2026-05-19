"""Drift-lock pin: every alembic revision under ``alembic/versions/`` must
define a non-trivial ``downgrade()`` body.

Cycle 60 — MH-DRIFTLOCK-MIGRATION-DOWNGRADE-PRESENT.

Why this pin exists
-------------------
A revision whose ``downgrade()`` body is empty / ``pass`` / docstring-only
silently breaks the rollback path: ``alembic downgrade`` will appear to
succeed but will leave schema state diverged from logical version, which
is unrecoverable without manual SQL.  This is dangerous for any future
migration that touches a safety-critical column.

This test does NOT require downgrade SQL to be *correct* (that requires
real DB execution), only that a real implementation is present.

Test-only / additive: zero edits under ``apps/api/app/``; no migration.
"""

from __future__ import annotations

import ast
from pathlib import Path

VERSIONS_DIR = (
    Path(__file__).resolve().parent.parent / "alembic" / "versions"
)

# 31 real revisions present at cycle 60 (excluding __init__.py).  This count
# floor catches accidental deletions; new revisions raise it additively.
EXPECTED_MIN_REVISION_COUNT = 31

# If a revision is intentionally non-reversible (e.g. data backfill), add it
# here with a one-line justification recorded in docs/build-ledger.md.
KNOWN_NON_REVERSIBLE: set[str] = set()


def _iter_revision_files() -> list[Path]:
    return sorted(
        p for p in VERSIONS_DIR.glob("*.py") if p.name != "__init__.py"
    )


def _downgrade_body_kind(path: Path) -> tuple[bool, str | None]:
    """Return (has_downgrade, body_kind).

    body_kind ∈ {"pass", "docstring-only", "real:<n>"} where n is the
    number of statements in the body.  None if no downgrade() found.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "downgrade":
            body = node.body
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                return True, "pass"
            if (
                len(body) == 1
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                return True, "docstring-only"
            return True, f"real:{len(body)}"
    return False, None


def test_revision_count_floor() -> None:
    files = _iter_revision_files()
    assert len(files) >= EXPECTED_MIN_REVISION_COUNT, (
        f"Alembic revision count regressed: found {len(files)}, expected at "
        f"least {EXPECTED_MIN_REVISION_COUNT}. A revision file may have been "
        "deleted; deletion of revisions corrupts the alembic chain."
    )


def test_every_revision_defines_downgrade() -> None:
    missing: list[str] = []
    for path in _iter_revision_files():
        has_down, _ = _downgrade_body_kind(path)
        if not has_down:
            missing.append(path.name)
    assert not missing, (
        "The following alembic revisions are missing a downgrade() function: "
        f"{missing}. Every revision MUST define downgrade() so the rollback "
        "path can be exercised in CI/staging."
    )


def test_no_revision_has_trivial_downgrade_body() -> None:
    """No downgrade() may be ``pass`` or docstring-only.

    Empty bodies silently break rollback: alembic reports success but the
    schema state drifts from the logical revision.
    """
    offenders: list[str] = []
    for path in _iter_revision_files():
        if path.stem in KNOWN_NON_REVERSIBLE:
            continue
        _, kind = _downgrade_body_kind(path)
        if kind in {"pass", "docstring-only"}:
            offenders.append(f"  {path.name}: downgrade body is {kind}")
    assert not offenders, (
        "Alembic revisions with trivial (pass / docstring-only) downgrade "
        "bodies detected. Either implement a real downgrade or add the "
        "revision to KNOWN_NON_REVERSIBLE with a ledger entry justifying "
        "the non-reversibility.\n" + "\n".join(offenders)
    )
