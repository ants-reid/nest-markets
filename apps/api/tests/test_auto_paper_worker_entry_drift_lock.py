"""Cycle 34 — Auto-paper worker entry-point drift-lock.

The ``AutoPaperTraderWorker`` must remain wired to the broker safety
seam exactly as shipped:

    * It must import ``BrokerService`` from ``app.services.broker_service``
      (so the gate-chain runs).
    * Its submission helper must call ``submit_auto_order`` (NOT
      ``submit_order`` — auto intent must NEVER be silently downgraded
      to manual intent, which would bypass ``assert_auto_trading_allowed``).
    * It must NOT import any concrete broker client / adapter / gateway
      (``IBKRAdapter``, ``BrokerInterface``, ``BrokerGatewayFactory``)
      — any direct import would let the worker bypass the
      ``BrokerService`` seam entirely.
    * It must keep ``AutoTradingBlockedError`` imported so the
      gate-raise can be caught and recorded (rather than crashing the
      whole worker run).

Implemented as static AST scan of the worker source — no runtime
invocation of the worker, no DB.

Drift-lock notes:
    * Pure additive test; no production code change.
"""

from __future__ import annotations

import ast
from pathlib import Path

import app.workers.auto_paper_trader_worker as worker_module


WORKER_PATH = Path(worker_module.__file__)


def _parse() -> ast.Module:
    return ast.parse(WORKER_PATH.read_text(encoding="utf-8"))


def _imported_names(tree: ast.Module) -> dict[str, set[str]]:
    """Return ``{module_path: {imported_name, ...}}`` for every
    ``from <module> import <name>`` in the module."""
    result: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            result.setdefault(node.module, set()).update(
                alias.name for alias in node.names
            )
    return result


def _all_call_attr_names(tree: ast.Module) -> set[str]:
    """Return the set of attribute-call names invoked anywhere in the
    module (e.g. ``foo.bar()`` contributes ``"bar"``)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


# --------------------------------------------------------------------------- #
# Required imports                                                            #
# --------------------------------------------------------------------------- #


def test_worker_imports_broker_service():
    tree = _parse()
    imports = _imported_names(tree)
    assert "BrokerService" in imports.get("app.services.broker_service", set()), (
        "AutoPaperTraderWorker must import BrokerService from "
        "app.services.broker_service so its safety gate runs. If you "
        "intend to change the seam, ship a matrix phase + ledger entry."
    )


def test_worker_imports_auto_trading_blocked_error():
    tree = _parse()
    imports = _imported_names(tree)
    assert "AutoTradingBlockedError" in imports.get(
        "app.services.trading_control_service", set()
    ), (
        "AutoPaperTraderWorker must import AutoTradingBlockedError from "
        "app.services.trading_control_service so the gate-raise can be "
        "caught and recorded. Removing this import means the worker "
        "would crash on every gate-block instead of recording it."
    )


# --------------------------------------------------------------------------- #
# Forbidden imports — the worker MUST NOT bypass the BrokerService seam.      #
# --------------------------------------------------------------------------- #


# Forbidden module → set of forbidden symbol names. ``OrderRequest`` /
# ``OrderResult`` are pure data classes living in ``broker_interface`` and
# ARE allowed (the worker constructs ``OrderRequest`` to hand to
# ``BrokerService``). Any *behavioural* broker symbol from the same module
# is forbidden.
FORBIDDEN_IMPORTS: dict[str, set[str]] = {
    "app.clients.broker.broker_interface": {"BrokerInterface"},
    "app.clients.broker.ibkr_adapter": {"IBKRAdapter"},
    "app.clients.broker.gateway_factory": {"BrokerGatewayFactory"},
}


def test_worker_does_not_import_concrete_broker_client():
    tree = _parse()
    imports = _imported_names(tree)
    offenders: list[str] = []
    for module, forbidden_names in FORBIDDEN_IMPORTS.items():
        imported = imports.get(module, set())
        intersection = imported & forbidden_names
        if intersection:
            offenders.append(f"{module} imports {sorted(intersection)}")
    assert not offenders, (
        "AutoPaperTraderWorker imports concrete broker symbols that "
        f"would bypass the BrokerService seam: {offenders}. The worker "
        "must route through BrokerService.submit_auto_order(...) so "
        "the trading_control_service gate runs."
    )


# --------------------------------------------------------------------------- #
# Submission verb — must be submit_auto_order (NOT submit_order).             #
# --------------------------------------------------------------------------- #


def test_worker_calls_submit_auto_order_not_submit_order():
    tree = _parse()
    attr_calls = _all_call_attr_names(tree)
    assert "submit_auto_order" in attr_calls, (
        "AutoPaperTraderWorker must call ``.submit_auto_order(...)`` "
        "on the broker service. If this name disappears, the auto path "
        "may have been silently rerouted through the manual seam — ship "
        "a matrix phase + ledger entry."
    )
    assert "submit_order" not in attr_calls, (
        "AutoPaperTraderWorker must NOT call ``.submit_order(...)`` — "
        "that is the manual-intent seam and would bypass "
        "assert_auto_trading_allowed(). Found a call site; ship a "
        "matrix phase + ledger entry if intentional."
    )


def test_worker_acquires_broker_service_via_factory_method():
    """The worker must obtain the broker service via its own
    ``_get_broker_service()`` factory method (so tests can monkey-patch
    a fake) rather than constructing ``BrokerService()`` inline at
    every call site."""
    tree = _parse()
    attr_calls = _all_call_attr_names(tree)
    assert "_get_broker_service" in attr_calls, (
        "AutoPaperTraderWorker must acquire its BrokerService via the "
        "``_get_broker_service()`` factory method (not inline "
        "construction at every call site). This is the seam tests rely "
        "on for monkey-patching."
    )
