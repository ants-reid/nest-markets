"""MH-DRIFTLOCK-BROKER-MODE-GUARD-EXCEPTION-HIERARCHY-PIN

Pins three facts about the broker-mode-guard exception classes:
  1. All three names exist and are subclasses of ``Exception`` (so
     ``except Exception`` safety wrappers continue to catch them).
  2. ``BrokerModeInconsistencyError`` is an alias for
     ``LiveExecutionBlockedError`` (silently decoupling the alias would
     change which `except` clauses catch what).
  3. ``TradingControlMisconfiguredError`` inherits from
     ``TradingControlError`` (chained safety hierarchy must remain).
"""
from __future__ import annotations

from app.services.broker_mode_guard import (
    BrokerModeInconsistencyError,
    LiveExecutionBlockedError,
    TradingControlMisconfiguredError,
)
from app.services.trading_control_service import TradingControlError

_EXCEPTIONS: tuple[type[BaseException], ...] = (
    BrokerModeInconsistencyError,
    LiveExecutionBlockedError,
    TradingControlMisconfiguredError,
)


def test_broker_mode_guard_exceptions_inherit_from_exception() -> None:
    for cls in _EXCEPTIONS:
        assert issubclass(cls, Exception), (
            f"{cls.__name__} must inherit from Exception, not BaseException — "
            "re-parenting would escape `except Exception` safety wrappers."
        )


def test_broker_mode_inconsistency_aliases_live_execution_blocked() -> None:
    assert BrokerModeInconsistencyError is LiveExecutionBlockedError, (
        "BrokerModeInconsistencyError must remain an alias for LiveExecutionBlockedError. "
        "Decoupling would silently change which `except` clauses catch what."
    )


def test_trading_control_misconfigured_inherits_trading_control_error() -> None:
    assert issubclass(TradingControlMisconfiguredError, TradingControlError), (
        "TradingControlMisconfiguredError must remain a subclass of TradingControlError "
        "so safety code that catches the parent continues to catch this case."
    )
