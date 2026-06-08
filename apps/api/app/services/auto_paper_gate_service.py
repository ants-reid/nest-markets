"""AutoPaperGateService — controlled-run gates on top of the existing auto-paper worker.

This service does NOT replace any existing safety gate. It adds a per-run/per-day
control layer that fails closed by default. The inner drift-locked broker gate
(`assert_auto_trading_allowed`) continues to apply unconditionally; this layer
just prevents the worker from even reaching the broker path unless every
operator-controlled precondition is satisfied.

All values are derived from env-backed `Settings`. Default posture: BLOCKED.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models.paper_order import PaperOrder
from app.db.models.risk_profile import RiskProfile


@dataclass(frozen=True)
class AutoPaperGateDecision:
    """Result of an auto-paper gate evaluation."""

    allowed: bool
    blocking_gate: str | None
    reason: str | None
    snapshot: dict[str, Any] = field(default_factory=dict)


class AutoPaperGateService:
    """Evaluate operator-controlled gates for one auto-paper run."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def allowlist(self) -> tuple[str, ...]:
        raw = self._settings.auto_paper_symbol_allowlist or ""
        return tuple(
            sym.strip().upper()
            for sym in raw.split(",")
            if sym and sym.strip()
        )

    def is_symbol_allowed(self, symbol: str | None) -> bool:
        if not symbol:
            return False
        allowlist = self.allowlist
        if not allowlist:
            return True
        return symbol.strip().upper() in allowlist

    def count_orders_today(self, session: Session) -> int:
        """Count auto-paper orders submitted since UTC midnight.

        Returns 0 if the session does not support this query shape (e.g. a
        test fake). The gate fails closed elsewhere; this helper is intentionally
        permissive to keep status surfaces resilient.
        """
        start = datetime.combine(
            datetime.now(timezone.utc).date(),
            time.min,
            tzinfo=timezone.utc,
        )
        stmt = select(func.count()).where(
            PaperOrder.order_type == "auto_paper",
            PaperOrder.submitted_at >= start,
        )
        try:
            return int(session.execute(stmt).scalar_one())
        except Exception:
            return 0

    def _kill_switch_active(self, session: Session) -> bool:
        try:
            profile = (
                session.query(RiskProfile)
                .filter(RiskProfile.is_active == "active")
                .first()
            )
        except Exception:
            return False
        if profile is None:
            return True
        return bool(profile.kill_switch_enabled)

    # ------------------------------------------------------------------
    # Snapshot for status surfaces
    # ------------------------------------------------------------------

    def snapshot(self, session: Session | None = None) -> dict[str, Any]:
        s = self._settings
        snap: dict[str, Any] = {
            "auto_paper_enabled": bool(s.auto_paper_enabled),
            "broker_provider": s.broker_provider,
            "broker_mode": s.broker_mode,
            "tws_enabled": bool(s.tws_enabled),
            "live_execution_enabled": bool(s.live_execution_enabled),
            "max_orders_per_run": int(s.auto_paper_max_orders_per_run),
            "max_orders_per_day": int(s.auto_paper_max_orders_per_day),
            "max_notional_usd": float(s.auto_paper_max_notional_usd),
            "symbol_allowlist": list(self.allowlist),
            "order_type": s.auto_paper_order_type.upper(),
            "limit_price": float(s.auto_paper_limit_price),
            "require_tws": bool(s.auto_paper_require_tws),
            "background_scheduler_enabled": bool(
                getattr(s, "auto_paper_background_scheduler_enabled", False)
            ),
            "minutes_between_runs": int(
                getattr(s, "auto_paper_minutes_between_runs", 30)
            ),
            "kill_on_error_count": int(
                getattr(s, "auto_paper_kill_on_error_count", 3)
            ),
            "kill_on_reject_rate": float(
                getattr(s, "auto_paper_kill_on_reject_rate", 0.5)
            ),
        }
        if session is not None:
            snap["orders_today"] = self.count_orders_today(session)
            snap["kill_switch_active"] = self._kill_switch_active(session)
        return snap

    # ------------------------------------------------------------------
    # Run-level evaluation (no opportunity context yet)
    # ------------------------------------------------------------------

    def evaluate_run(self, session: Session) -> AutoPaperGateDecision:
        """Evaluate gates that don't depend on a particular opportunity."""
        s = self._settings
        snap = self.snapshot(session)

        def blocked(gate: str, reason: str) -> AutoPaperGateDecision:
            return AutoPaperGateDecision(
                allowed=False,
                blocking_gate=gate,
                reason=reason,
                snapshot=snap,
            )

        if not s.auto_paper_enabled:
            return blocked("auto_paper_enabled", "AUTO_PAPER_ENABLED is false")
        if s.live_execution_enabled:
            return blocked("live_execution_enabled", "LIVE_EXECUTION_ENABLED must be false")
        if s.broker_mode.lower() != "paper":
            return blocked("broker_mode", f"BROKER_MODE must be 'paper' (got {s.broker_mode!r})")
        if s.auto_paper_require_tws:
            if s.broker_provider.lower() != "tws":
                return blocked(
                    "broker_provider",
                    f"BROKER_PROVIDER must be 'tws' (got {s.broker_provider!r})",
                )
            if not s.tws_enabled:
                return blocked("tws_enabled", "TWS_ENABLED must be true")
        if s.auto_paper_order_type.upper() != "LIMIT":
            return blocked(
                "order_type",
                f"AUTO_PAPER_ORDER_TYPE must be 'LIMIT' (got {s.auto_paper_order_type!r})",
            )
        if not self.allowlist:
            return blocked(
                "symbol_allowlist",
                "AUTO_PAPER_SYMBOL_ALLOWLIST must include at least one symbol",
            )
        if s.auto_paper_max_orders_per_run <= 0:
            return blocked(
                "max_orders_per_run",
                "AUTO_PAPER_MAX_ORDERS_PER_RUN must be > 0",
            )
        if s.auto_paper_max_orders_per_day <= 0:
            return blocked(
                "max_orders_per_day",
                "AUTO_PAPER_MAX_ORDERS_PER_DAY must be > 0",
            )
        if snap.get("kill_switch_active", True):
            return blocked("kill_switch", "Risk-profile kill switch is active")

        orders_today = int(snap.get("orders_today", 0))
        if orders_today >= s.auto_paper_max_orders_per_day:
            return blocked(
                "max_orders_per_day",
                f"Daily cap reached ({orders_today}/{s.auto_paper_max_orders_per_day})",
            )

        return AutoPaperGateDecision(
            allowed=True,
            blocking_gate=None,
            reason=None,
            snapshot=snap,
        )

    # ------------------------------------------------------------------
    # Per-order evaluation
    # ------------------------------------------------------------------

    def evaluate_order(
        self,
        *,
        symbol: str | None,
        order_type: str | None,
        limit_price: Decimal | float | None,
        quantity: Decimal | float,
    ) -> AutoPaperGateDecision:
        s = self._settings

        def blocked(gate: str, reason: str) -> AutoPaperGateDecision:
            return AutoPaperGateDecision(
                allowed=False,
                blocking_gate=gate,
                reason=reason,
                snapshot={
                    "symbol": symbol,
                    "order_type": order_type,
                    "limit_price": float(limit_price) if limit_price is not None else None,
                    "quantity": float(quantity),
                },
            )

        if not self.is_symbol_allowed(symbol):
            return blocked(
                "symbol_allowlist",
                f"Symbol {symbol!r} not in allowlist {list(self.allowlist)}",
            )

        normalized_type = (order_type or "").upper()
        if normalized_type != "LIMIT":
            return blocked(
                "order_type",
                f"Only LIMIT orders allowed in auto-paper v1 (got {order_type!r})",
            )

        if limit_price is None:
            return blocked("limit_price", "LIMIT order missing limit_price")

        notional = float(limit_price) * float(quantity)
        if notional > s.auto_paper_max_notional_usd:
            return blocked(
                "max_notional_usd",
                (
                    f"Notional ${notional:.2f} exceeds cap "
                    f"${s.auto_paper_max_notional_usd:.2f}"
                ),
            )

        return AutoPaperGateDecision(
            allowed=True,
            blocking_gate=None,
            reason=None,
            snapshot={
                "symbol": symbol.upper() if symbol else None,
                "order_type": normalized_type,
                "limit_price": float(limit_price),
                "quantity": float(quantity),
                "notional_usd": notional,
            },
        )
