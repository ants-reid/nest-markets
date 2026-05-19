"""MH-DRIFTLOCK-LIVE-EXECUTION-SUBMIT-SAFETY-TOKEN-PIN

Token-level guard on ``LiveExecutionService.submit`` body — complements
the byte-exact SHA pin from cycle 76 with semantic guarantees that
``auto_live`` is gated and the disabled-sentinel reason string is
present. Token drift fails loudly even when whitespace edits don't
trip the SHA pin.
"""
from __future__ import annotations

import inspect

from app.services.live_execution_service import LiveExecutionService

_REQUIRED_TOKENS: tuple[str, ...] = (
    "auto_live",
    "live_execution_disabled_in_mvp",
    "is_paper_enabled",
)


def test_live_execution_submit_safety_tokens_present() -> None:
    src = inspect.getsource(LiveExecutionService.submit)
    missing = [t for t in _REQUIRED_TOKENS if t not in src]
    assert not missing, (
        f"LiveExecutionService.submit lost safety tokens {missing!r}. "
        "These tokens enforce the auto_live disabled-sentinel and paper-enabled gate."
    )
