"""Cycle 35 — Static drift-lock for the paper-mode preflight enforcement.

Asserts (via AST scan of ``app/services/broker_service.py``) that the
paper-mode branch of ``BrokerService._submit_order_for_intent`` retains
its preflight enforcement structure:

    if trading_mode == "paper":
        ... dry_run_order(...) ...
        if blocking_count > 0 or would_block_count > 0:
            raise PaperPreflightBlockedError(...)

This is the deterministic "paper trade gets blocked when preflight is
unhappy" gate. If the dry-run call disappears, or the
``PaperPreflightBlockedError`` raise becomes conditional on something
weaker than ``blocking_count > 0 or would_block_count > 0``, the gate
is silently weakened.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Source file is read as text and AST-parsed; no runtime invocation
      of ``BrokerService`` or ``trading_control_service``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import app.services.broker_service as broker_service_module


BROKER_SERVICE_PATH = Path(broker_service_module.__file__)


def _parse() -> ast.Module:
    return ast.parse(BROKER_SERVICE_PATH.read_text(encoding="utf-8"))


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"Function/method ``{name}`` not found in AST")


def _calls_in(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    return [n for n in ast.walk(func) if isinstance(n, ast.Call)]


def _raises_in(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Raise]:
    return [n for n in ast.walk(func) if isinstance(n, ast.Raise)]


# --------------------------------------------------------------------------- #
# Paper branch must call dry_run_order(...)                                   #
# --------------------------------------------------------------------------- #


def test_intent_router_calls_dry_run_order():
    """The paper-mode branch must invoke ``dry_run_order(...)`` to
    populate the preflight decision before any broker submit."""
    tree = _parse()
    func = _find_function(tree, "_submit_order_for_intent")
    found = False
    for call in _calls_in(func):
        callee = call.func
        if isinstance(callee, ast.Attribute) and callee.attr == "dry_run_order":
            found = True
            break
        if isinstance(callee, ast.Name) and callee.id == "dry_run_order":
            found = True
            break
    assert found, (
        "BrokerService._submit_order_for_intent must call "
        "dry_run_order(...) on the paper branch. If you intend to "
        "remove preflight, ship a matrix phase + ledger entry."
    )


# --------------------------------------------------------------------------- #
# Paper branch must raise PaperPreflightBlockedError                          #
# --------------------------------------------------------------------------- #


def test_intent_router_raises_paper_preflight_blocked_error():
    """The paper-mode branch must raise ``PaperPreflightBlockedError``
    somewhere in its body (i.e. when preflight returns a blocking
    decision)."""
    tree = _parse()
    func = _find_function(tree, "_submit_order_for_intent")
    found = False
    for raise_node in _raises_in(func):
        exc = raise_node.exc
        if exc is None:
            continue
        # `raise PaperPreflightBlockedError(...)` → exc is a Call whose .func is a Name.
        if isinstance(exc, ast.Call):
            callee = exc.func
            if isinstance(callee, ast.Name) and callee.id == "PaperPreflightBlockedError":
                found = True
                break
            if isinstance(callee, ast.Attribute) and callee.attr == "PaperPreflightBlockedError":
                found = True
                break
        # `raise PaperPreflightBlockedError` (bare class) → exc is a Name.
        if isinstance(exc, ast.Name) and exc.id == "PaperPreflightBlockedError":
            found = True
            break
    assert found, (
        "BrokerService._submit_order_for_intent must raise "
        "PaperPreflightBlockedError on the paper branch when preflight "
        "is blocking. If you intend to soften this gate, ship a matrix "
        "phase + ledger entry."
    )


# --------------------------------------------------------------------------- #
# The PaperPreflightBlockedError class still exists in the module             #
# --------------------------------------------------------------------------- #


def test_paper_preflight_blocked_error_is_exported():
    """Sanity: the exception class must remain part of the module's
    public surface so the worker can catch it."""
    assert hasattr(broker_service_module, "PaperPreflightBlockedError"), (
        "BrokerService module must continue to export "
        "PaperPreflightBlockedError so AutoPaperTraderWorker can catch it."
    )
    cls = broker_service_module.PaperPreflightBlockedError
    assert isinstance(cls, type), (
        "PaperPreflightBlockedError must be a class (got "
        f"{type(cls).__name__})."
    )
    assert issubclass(cls, Exception), (
        "PaperPreflightBlockedError must remain an Exception subclass."
    )


# --------------------------------------------------------------------------- #
# The blocking-decision condition references both block-count fields         #
# --------------------------------------------------------------------------- #


def test_intent_router_blocking_condition_checks_both_counts():
    """The blocking condition must reference *both* ``blocking_count``
    and ``would_block_count``. If only one is checked, half the failure
    modes are silently allowed through."""
    tree = _parse()
    func = _find_function(tree, "_submit_order_for_intent")
    src = ast.unparse(func)
    assert "blocking_count" in src, (
        "_submit_order_for_intent body no longer references "
        "``blocking_count`` — the strict-block half of the gate is gone."
    )
    assert "would_block_count" in src, (
        "_submit_order_for_intent body no longer references "
        "``would_block_count`` — the would-block half of the gate is gone."
    )
