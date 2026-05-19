"""MH-DRIFTLOCK-BROKER-MODE-GUARD-PUBLIC-API-CATALOG

Pins the public API surface of ``app.services.broker_mode_guard``: the
guard functions and the exception classes every safety caller relies on.
"""
from __future__ import annotations

from app.services import broker_mode_guard

_REQUIRED_FUNCTIONS: frozenset[str] = frozenset(
    {
        "assert_paper_mode",
        "assert_mode_configuration_consistent",
        "check_ibkr_gateway",
        "get_broker_mode_metadata",
        "is_live_mode_enabled",
        "is_paper_account_id",
    }
)

_REQUIRED_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "BrokerModeInconsistencyError",
        "LiveExecutionBlockedError",
        "TradingControlMisconfiguredError",
    }
)


def test_broker_mode_guard_required_functions_present() -> None:
    missing = [
        n for n in _REQUIRED_FUNCTIONS
        if not callable(getattr(broker_mode_guard, n, None))
    ]
    assert not missing, f"broker_mode_guard missing required functions: {sorted(missing)}"


def test_broker_mode_guard_required_exception_classes_present() -> None:
    missing = []
    for n in _REQUIRED_EXCEPTIONS:
        cls = getattr(broker_mode_guard, n, None)
        if not (isinstance(cls, type) and issubclass(cls, BaseException)):
            missing.append(n)
    assert not missing, f"broker_mode_guard missing required exception classes: {sorted(missing)}"


def test_broker_mode_guard_assert_paper_mode_no_args() -> None:
    import inspect
    sig = inspect.signature(broker_mode_guard.assert_paper_mode)
    # Allow one optional argument at most (e.g. settings override); guard
    # against silent injection of a 'force' bypass parameter.
    assert len(sig.parameters) <= 1, (
        f"assert_paper_mode signature widened: {list(sig.parameters)!r}"
    )
