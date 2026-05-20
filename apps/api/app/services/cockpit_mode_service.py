"""MH-COCKPIT-03 — safe cockpit mode selector service.

This service exposes an operator-facing mode selection surface without changing
broker execution behaviour or weakening any existing backend guard.

The selected cockpit mode is a UI/runtime preference only in this phase. The
true execution boundary remains owned by trading_control_service and related
live/paper guards.
"""

from __future__ import annotations

from threading import Lock

from fastapi import HTTPException

from app.schemas.cockpit_mode import (
    CockpitModeOptionSchema,
    CockpitModeResponseSchema,
    CockpitModeSafetyStateSchema,
)
from app.services.trading_control_service import TradingControlState, get_trading_mode

SELECTABLE_MODES = ("learning", "manual", "auto_paper")
LOCKED_MODES = ("assisted_live", "live", "auto_live")
DEFAULT_MODE = "learning"

_mode_lock = Lock()
_selected_mode = DEFAULT_MODE


def _get_selected_mode() -> str:
    with _mode_lock:
        return _selected_mode


def _set_selected_mode(value: str) -> str:
    global _selected_mode
    with _mode_lock:
        _selected_mode = value
        return _selected_mode


def _serialize_safety_state(state: TradingControlState) -> CockpitModeSafetyStateSchema:
    return CockpitModeSafetyStateSchema(
        live_trading_enabled=False,
        auto_live_enabled=False,
        real_money_enabled=False,
        paper_order_submission_allowed=state.paper_order_submission_allowed,
        live_order_submission_allowed=state.live_order_submission_allowed,
        auto_trading_allowed=state.auto_trading_allowed,
        emergency_stop_active=state.emergency_stop_active,
        trading_mode=state.trading_mode,
        execution_control=state.execution_control,
        arming_state=state.arming_state,
        reasons=list(state.reasons),
    )


def _build_mode_options(current_mode: str) -> list[CockpitModeOptionSchema]:
    active = current_mode
    return [
        CockpitModeOptionSchema(
            id="learning",
            label="Learning",
            status="active" if active == "learning" else "available",
            selectable=True,
            locked=False,
            reason="No orders are placed. This mode is for learning, explanations, and observation only.",
            risk_note="Risk first: no paper or live orders are submitted from Learning mode.",
            allowed_actions=[
                "Read explanations and market context",
                "Review practice recommendations",
                "Inspect cockpit safety posture",
            ],
            blocked_actions=[
                "Paper order automation",
                "Live broker submission",
                "Real-money trading",
            ],
            safety_gates=[
                "No order path is enabled by mode selection",
                "Live trading remains blocked in backend guards",
            ],
        ),
        CockpitModeOptionSchema(
            id="manual",
            label="Manual",
            status="active" if active == "manual" else "available",
            selectable=True,
            locked=False,
            reason="Nothing is submitted unless the operator explicitly chooses to act.",
            risk_note="Risk first: recommendations stay advisory until a human reviews and confirms the next step.",
            allowed_actions=[
                "Review recommendations and reasoning",
                "Inspect manual paper trading posture",
                "Decide manually whether to continue in other approved surfaces",
            ],
            blocked_actions=[
                "Automatic paper trading",
                "Live auto-approval",
                "Real-money submission",
            ],
            safety_gates=[
                "Existing trading_control_service rules still apply",
                "Live order submission remains blocked",
            ],
        ),
        CockpitModeOptionSchema(
            id="auto_paper",
            label="Auto Paper",
            status="active" if active == "auto_paper" else "available",
            selectable=True,
            locked=False,
            reason="Simulation only. This mode signals paper-only operator intent and keeps real money out of scope.",
            risk_note="Risk first: selecting Auto Paper does not enable live trading and does not bypass paper-boundary checks.",
            allowed_actions=[
                "View auto-paper readiness and status surfaces",
                "Operate inside the paper/simulation boundary",
                "Keep live and real-money paths disabled",
            ],
            blocked_actions=[
                "Real broker order routing",
                "Auto live trading",
                "Risk-control bypass",
            ],
            safety_gates=[
                "Backend live flags remain false",
                "Existing auto-trading enforcement still owns execution eligibility",
            ],
        ),
        CockpitModeOptionSchema(
            id="assisted_live",
            label="Assisted Live",
            status="locked",
            selectable=False,
            locked=True,
            reason="Locked until a future live-readiness checklist, per-trade approval flow, and explicit unlock phase exist.",
            risk_note="Risk first: assisted live stays unavailable because current protections are not sufficient for real-money routing.",
            allowed_actions=["Review future product direction only"],
            blocked_actions=["Mode selection", "Live order submission", "Real-money trading"],
            safety_gates=[
                "Rejected server-side if requested",
                "Frontend disabled state is informational only",
            ],
        ),
        CockpitModeOptionSchema(
            id="live",
            label="Live / Real Money",
            status="locked",
            selectable=False,
            locked=True,
            reason="Locked until future live arming, emergency-stop, and release-checklist phases are complete.",
            risk_note="Risk first: real-money trading remains blocked even if a client edits the frontend.",
            allowed_actions=["Review future product direction only"],
            blocked_actions=["Mode selection", "Live order submission", "Real-money trading"],
            safety_gates=[
                "Rejected server-side if requested",
                "live_trading_enabled remains false",
            ],
        ),
        CockpitModeOptionSchema(
            id="auto_live",
            label="Auto Live",
            status="locked",
            selectable=False,
            locked=True,
            reason="Locked until long paper evidence, positive expectancy review, safety sign-off, and explicit unlock exist.",
            risk_note="Risk first: auto live is intentionally blocked because the current build does not permit automated real-money execution.",
            allowed_actions=["Review future product direction only"],
            blocked_actions=["Mode selection", "Automatic live trading", "Real-money trading"],
            safety_gates=[
                "Rejected server-side if requested",
                "auto_live_enabled remains false",
            ],
        ),
    ]


def get_cockpit_mode_state(
    *,
    trading_control_state: TradingControlState | None = None,
) -> CockpitModeResponseSchema:
    state = trading_control_state or get_trading_mode()
    current_mode = _get_selected_mode()
    safety = _serialize_safety_state(state)
    return CockpitModeResponseSchema(
        current_mode=current_mode,
        selectable_modes=list(SELECTABLE_MODES),
        locked_modes=list(LOCKED_MODES),
        modes=_build_mode_options(current_mode),
        global_safety_state=safety,
        live_trading_enabled=False,
        auto_live_enabled=False,
        real_money_enabled=False,
        notes=[
            "Mode selection is advisory and does not replace backend trading guards.",
            "Live and real-money modes stay blocked in this phase even if a client submits them directly.",
            "Auto Paper remains inside the existing paper/simulation boundary only.",
        ],
    )


def set_cockpit_mode(
    requested_mode: str,
    *,
    trading_control_state: TradingControlState | None = None,
) -> CockpitModeResponseSchema:
    normalized = requested_mode.strip().lower()
    if normalized in LOCKED_MODES:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "cockpit_mode_locked",
                "requested_mode": normalized,
                "message": "This mode is visible for product direction only and remains locked in the current build.",
            },
        )
    if normalized not in SELECTABLE_MODES:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "cockpit_mode_invalid",
                "requested_mode": normalized,
                "message": "Unsupported cockpit mode requested.",
            },
        )

    _set_selected_mode(normalized)
    return get_cockpit_mode_state(trading_control_state=trading_control_state)


def reset_cockpit_mode_for_tests() -> None:
    _set_selected_mode(DEFAULT_MODE)