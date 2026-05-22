"""Deferred-writer drift-lock tests.

Two matrix entries ship additive columns but explicitly defer writers:

    * MH-153-A — ``risk_decisions.risk_profile_id`` column.
            Writer (MH-153-B) remains deferred.
    * MH-154-A — ``risk_decisions.block_reason_code`` column.
            Writer (MH-154-B) remains deferred.

Until those writers are formally unlocked in the matrix, NO production code
under ``app/services/`` or ``app/workers/`` may assign to
``risk_profile_id=`` / ``block_reason_code=`` on ``RiskDecision`` instances.

These tests use static AST scanning so they:
    * are fast and deterministic,
    * do not touch the DB,
    * fire even when ``APP_ENV=test`` disables the scheduler/lifespan,
    * cannot be skipped by mocking.

Drift-lock notes:
    * Pure additive tests; no production code change.
    * No imports of ``trading_control_service``, ``BrokerService``, or
      worker runtime modules (only their *source files* are read as text
      and AST-parsed).
"""

from __future__ import annotations

import ast
from pathlib import Path

import app.db.models.risk_decision as risk_decision_module


# Path roots that MUST NOT contain a writer for any of the three deferred
# surfaces. Routes are explicitly EXCLUDED — read-only routes legitimately
# read these columns/tables for surfacing in the audit hub.
SCAN_ROOTS: tuple[str, ...] = ("app/services", "app/workers")

# Repo root — derive from the model module location (apps/api/app/db/models/...)
APPS_API_ROOT = Path(risk_decision_module.__file__).parents[3]


def _iter_python_sources(root_subdir: str) -> list[Path]:
    """Return every ``.py`` file under ``apps/api/<root_subdir>/``."""
    root = APPS_API_ROOT / root_subdir
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _find_keyword_assignments(source: str, kwarg_name: str) -> bool:
    """Return True if ``kwarg_name=...`` appears as a keyword argument in any
    Call expression in ``source``."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == kwarg_name:
                    return True
    return False


def _find_attribute_assignments(source: str, attr_name: str) -> bool:
    """Return True if ``<expr>.<attr_name> = ...`` appears as a statement."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            for tgt in targets:
                if isinstance(tgt, ast.Attribute) and tgt.attr == attr_name:
                    return True
    return False


def _find_constructor_call(source: str, class_name: str) -> bool:
    """Return True if ``class_name(...)`` is invoked (by bare name) in source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == class_name:
                return True
            if isinstance(func, ast.Attribute) and func.attr == class_name:
                return True
    return False


# --------------------------------------------------------------------------- #
# Sanity: the modules under test exist and expose the expected surface.       #
# --------------------------------------------------------------------------- #


def test_risk_decision_model_still_exposes_deferred_columns():
    """Sanity check: the columns the drift-lock guards must still exist on
    the model. If somebody dropped them, this test fails before the
    drift-lock checks below would silently pass."""
    cols = risk_decision_module.RiskDecision.__table__.columns
    assert "risk_profile_id" in cols, "MH-153-A column missing"
    assert "block_reason_code" in cols, "MH-154-A column missing"


# --------------------------------------------------------------------------- #
# MH-153-A drift lock — no writer for ``risk_profile_id``.                    #
# --------------------------------------------------------------------------- #


def test_no_production_writer_for_risk_profile_id():
    """No service or worker may set ``risk_profile_id=...`` (kwarg) or
    ``<row>.risk_profile_id = ...`` (attribute assignment) until MH-153-B
    is formally unlocked in the matrix."""
    offenders: list[str] = []
    for root in SCAN_ROOTS:
        for path in _iter_python_sources(root):
            src = path.read_text(encoding="utf-8")
            if _find_keyword_assignments(src, "risk_profile_id"):
                offenders.append(f"{path.relative_to(APPS_API_ROOT)} (kwarg)")
            if _find_attribute_assignments(src, "risk_profile_id"):
                offenders.append(f"{path.relative_to(APPS_API_ROOT)} (attr)")
    assert not offenders, (
        "MH-153-B writer is deferred — no production code in app/services or "
        "app/workers may write to ``risk_profile_id`` yet. Offenders: "
        f"{offenders}. To enable, ship MH-153-B as its own matrix phase + "
        "ledger entry and update this test."
    )


# --------------------------------------------------------------------------- #
# MH-154-A drift lock — no writer for ``block_reason_code``.                  #
# --------------------------------------------------------------------------- #


def test_no_production_writer_for_block_reason_code():
    """No service or worker may set ``block_reason_code=...`` (kwarg) or
    ``<row>.block_reason_code = ...`` (attribute assignment) until
    MH-154-B is formally unlocked in the matrix."""
    offenders: list[str] = []
    for root in SCAN_ROOTS:
        for path in _iter_python_sources(root):
            src = path.read_text(encoding="utf-8")
            if _find_keyword_assignments(src, "block_reason_code"):
                offenders.append(f"{path.relative_to(APPS_API_ROOT)} (kwarg)")
            if _find_attribute_assignments(src, "block_reason_code"):
                offenders.append(f"{path.relative_to(APPS_API_ROOT)} (attr)")
    assert not offenders, (
        "MH-154-B writer is deferred — no production code in app/services or "
        "app/workers may write to ``block_reason_code`` yet. Offenders: "
        f"{offenders}. To enable, ship MH-154-B as its own matrix phase + "
        "ledger entry and update this test."
    )

