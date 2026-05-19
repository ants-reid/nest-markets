"""Cycle 33 — Static drift-lock for the broker-gate enforcement chain.

Asserts (via AST scan of the *source files*, no runtime imports of
``trading_control_service`` or ``BrokerService`` aside from path
discovery) that the four-link enforcement chain is structurally intact:

    BrokerService.submit_auto_order(...)
        → BrokerService._submit_order_for_intent(..., intent="auto")
            → assert_order_submission_allowed(intent="auto")
                → assert_auto_trading_allowed()
                    → raises AutoTradingBlockedError unconditionally

If any link is silently rewired, broken, or short-circuited, these
tests fail with a directive to ship a named matrix phase + ledger
entry.

Drift-lock notes:
    * Pure additive tests; no production code change.
    * Source files are read as text and AST-parsed; no runtime
      behaviour invocation of the enforcement chain.
"""

from __future__ import annotations

import ast
from pathlib import Path

import app.services.broker_service as broker_service_module
import app.services.trading_control_service as trading_control_service_module


BROKER_SERVICE_PATH = Path(broker_service_module.__file__)
TRADING_CONTROL_PATH = Path(trading_control_service_module.__file__)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """Find a top-level function or method definition by name (DFS).

    Searches both module-level and class-level scopes.
    """
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"Function/method ``{name}`` not found in AST")


def _calls_in(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    return [n for n in ast.walk(func) if isinstance(n, ast.Call)]


def _has_call_with_kwarg(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    callee_attr_or_name: str,
    kwarg_name: str,
    kwarg_value: str,
) -> bool:
    """Return True if ``func`` body contains a call ``...callee(..., kwarg_name=kwarg_value)``."""
    for call in _calls_in(func):
        callee_match = False
        if isinstance(call.func, ast.Attribute) and call.func.attr == callee_attr_or_name:
            callee_match = True
        elif isinstance(call.func, ast.Name) and call.func.id == callee_attr_or_name:
            callee_match = True
        if not callee_match:
            continue
        for kw in call.keywords:
            if (
                kw.arg == kwarg_name
                and isinstance(kw.value, ast.Constant)
                and kw.value.value == kwarg_value
            ):
                return True
    return False


def _has_call_named(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    callee_name: str,
) -> bool:
    """Return True if ``func`` body contains any call to ``callee_name``
    (matched as bare name OR final attribute segment)."""
    for call in _calls_in(func):
        if isinstance(call.func, ast.Name) and call.func.id == callee_name:
            return True
        if isinstance(call.func, ast.Attribute) and call.func.attr == callee_name:
            return True
    return False


# --------------------------------------------------------------------------- #
# Link 1: submit_auto_order → _submit_order_for_intent(intent="auto")         #
# --------------------------------------------------------------------------- #


def test_submit_auto_order_delegates_to_intent_router_with_auto():
    tree = _parse(BROKER_SERVICE_PATH)
    func = _find_function(tree, "submit_auto_order")
    assert _has_call_with_kwarg(
        func, "_submit_order_for_intent", "intent", "auto"
    ), (
        "BrokerService.submit_auto_order must delegate to "
        '_submit_order_for_intent(..., intent="auto"). If you intend to '
        "change this seam, ship MH-AUTO-PATH-REWIRE as its own matrix "
        "phase + ledger entry and update this test."
    )


# --------------------------------------------------------------------------- #
# Link 2: _submit_order_for_intent → assert_order_submission_allowed          #
# --------------------------------------------------------------------------- #


def test_intent_router_calls_assert_order_submission_allowed():
    tree = _parse(BROKER_SERVICE_PATH)
    func = _find_function(tree, "_submit_order_for_intent")
    assert _has_call_named(func, "assert_order_submission_allowed"), (
        "BrokerService._submit_order_for_intent must call "
        "assert_order_submission_allowed(...) before any broker call. If "
        "you intend to relax this gate, ship a matrix phase + ledger "
        "entry and update this test."
    )


# --------------------------------------------------------------------------- #
# Link 3: assert_order_submission_allowed → assert_auto_trading_allowed       #
# --------------------------------------------------------------------------- #


def test_order_submission_allowed_routes_auto_to_auto_blocker():
    tree = _parse(TRADING_CONTROL_PATH)
    func = _find_function(tree, "assert_order_submission_allowed")
    assert _has_call_named(func, "assert_auto_trading_allowed"), (
        "assert_order_submission_allowed must invoke "
        "assert_auto_trading_allowed() on the auto branch. If you intend "
        "to change the auto routing, ship a matrix phase + ledger entry "
        "and update this test."
    )


# --------------------------------------------------------------------------- #
# Link 4: assert_auto_trading_allowed body unconditionally raises             #
# --------------------------------------------------------------------------- #


def test_assert_auto_trading_allowed_raises_unconditionally():
    """The body of ``assert_auto_trading_allowed`` must consist solely of
    a single ``raise ...`` statement (no conditional gates, no early
    returns, no flag checks). This is the *innermost* drift-lock — if it
    becomes conditional, auto trading can be silently enabled."""
    tree = _parse(TRADING_CONTROL_PATH)
    func = _find_function(tree, "assert_auto_trading_allowed")
    # Filter out docstring expression statements, count real statements.
    body = list(func.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    assert len(body) == 1, (
        f"assert_auto_trading_allowed body has {len(body)} statements; "
        "expected exactly 1 (a single unconditional raise). Any extra "
        "statement is a potential conditional bypass — ship a matrix "
        "phase + ledger entry if intentional."
    )
    assert isinstance(body[0], ast.Raise), (
        f"assert_auto_trading_allowed first non-docstring statement is "
        f"{type(body[0]).__name__}; expected ast.Raise."
    )

    # Runtime confirmation: the function must raise when called with no
    # arguments. Importing here is safe — this is a guard call, not an
    # enforcement-flip.
    import pytest

    from app.services.trading_control_service import (
        AutoTradingBlockedError,
        assert_auto_trading_allowed,
    )

    with pytest.raises(AutoTradingBlockedError):
        assert_auto_trading_allowed()
