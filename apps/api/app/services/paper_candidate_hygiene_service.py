"""Paper candidate queue hygiene maintainer.

This service is paper-candidate-only. It can run in dry-run mode to report
noise, and can optionally expire noisy candidate rows when explicitly applied.
It never submits orders and never touches paper order rows.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import SignalStatus
from app.db.models.asset import Asset
from app.db.models.signal import Signal

_DEFAULT_MAX_AGE_HOURS = 8
_DEFAULT_KEEP_PER_SYMBOL = 1
_MAX_AFFECTED_CANDIDATES = 50
_PAPER_TEST_PROVIDERS = (
    "paper_normal_refresh",
    "manual_paper_normal_seed",
    "manual_scheduler_seed",
)


@dataclass(frozen=True)
class _CandidateRow:
    signal_id: str
    symbol: str
    provider_name: str
    signal_status: str
    scan_ts: datetime | None
    signal_score: float
    reasons: tuple[str, ...]


class PaperCandidateHygieneService:
    """Detect and optionally clean noisy paper-test candidates."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def run(
        self,
        *,
        dry_run: bool = True,
        apply: bool = False,
        max_age_hours: int | None = None,
        keep_per_symbol: int = _DEFAULT_KEEP_PER_SYMBOL,
        allowlist_symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        max_age = int(max_age_hours or _DEFAULT_MAX_AGE_HOURS)
        keep_count = max(1, int(keep_per_symbol))
        allowlist = {symbol.strip().upper() for symbol in (allowlist_symbols or []) if symbol and symbol.strip()}

        candidate_rows = self._load_paper_test_candidates()
        now_utc = datetime.now(UTC)
        cutoff = now_utc - timedelta(hours=max_age)

        stale_ids: set[str] = set()
        duplicate_ids: set[str] = set()
        outside_allowlist_ids: set[str] = set()

        by_symbol: dict[str, list[Signal]] = defaultdict(list)
        for signal, asset in candidate_rows:
            symbol = asset.symbol.upper()
            by_symbol[symbol].append(signal)
            if signal.scan_ts is not None and signal.scan_ts < cutoff:
                stale_ids.add(str(signal.id))
            if allowlist and symbol not in allowlist:
                outside_allowlist_ids.add(str(signal.id))

        for symbol_signals in by_symbol.values():
            ordered = sorted(
                symbol_signals,
                key=lambda sig: (
                    sig.scan_ts if sig.scan_ts is not None else datetime.min.replace(tzinfo=UTC),
                    float(sig.signal_score or 0.0),
                    sig.created_at if sig.created_at is not None else datetime.min.replace(tzinfo=UTC),
                ),
                reverse=True,
            )
            for noisy_signal in ordered[keep_count:]:
                duplicate_ids.add(str(noisy_signal.id))

        all_target_ids = stale_ids | duplicate_ids | outside_allowlist_ids
        mutate_supported = hasattr(SignalStatus, "EXPIRED")
        should_apply = apply and (not dry_run) and mutate_supported

        updated_count = 0
        if should_apply and all_target_ids:
            updated_count = self._expire_candidates(all_target_ids)

        by_id = {
            str(signal.id): (signal, asset)
            for signal, asset in candidate_rows
        }
        affected = self._serialize_affected(
            by_id=by_id,
            stale_ids=stale_ids,
            duplicate_ids=duplicate_ids,
            outside_allowlist_ids=outside_allowlist_ids,
        )

        recommendations = self._build_recommendations(
            stale_count=len(stale_ids),
            duplicate_count=len(duplicate_ids),
            outside_allowlist_count=len(outside_allowlist_ids),
            mutate_supported=mutate_supported,
            dry_run=dry_run,
            apply=apply,
            updated_count=updated_count,
        )

        return {
            "dry_run": bool(dry_run),
            "apply": bool(apply),
            "stale_count": len(stale_ids),
            "duplicate_count": len(duplicate_ids),
            "outside_allowlist_count": len(outside_allowlist_ids),
            "would_update_count": len(all_target_ids),
            "updated_count": int(updated_count),
            "recommendations": recommendations,
            "affected_candidates": affected,
        }

    def _load_paper_test_candidates(self) -> list[tuple[Signal, Asset]]:
        return (
            self._session.execute(
                select(Signal, Asset)
                .join(Asset, Signal.asset_id == Asset.id)
                .where(Signal.signal_status == SignalStatus.CANDIDATE)
                .where(Signal.provider_name.in_(_PAPER_TEST_PROVIDERS))
            )
            .all()
        )

    def _expire_candidates(self, signal_ids: set[str]) -> int:
        rows = (
            self._session.execute(
                select(Signal)
                .where(Signal.id.in_(signal_ids))
                .where(Signal.signal_status == SignalStatus.CANDIDATE)
                .where(Signal.provider_name.in_(_PAPER_TEST_PROVIDERS))
            )
            .scalars()
            .all()
        )
        for signal in rows:
            signal.signal_status = SignalStatus.EXPIRED
        return len(rows)

    def _serialize_affected(
        self,
        *,
        by_id: dict[str, tuple[Signal, Asset]],
        stale_ids: set[str],
        duplicate_ids: set[str],
        outside_allowlist_ids: set[str],
    ) -> list[dict[str, Any]]:
        affected: list[dict[str, Any]] = []
        sorted_ids = sorted(stale_ids | duplicate_ids | outside_allowlist_ids)
        for signal_id in sorted_ids[:_MAX_AFFECTED_CANDIDATES]:
            signal, asset = by_id[signal_id]
            reasons: list[str] = []
            if signal_id in stale_ids:
                reasons.append("stale")
            if signal_id in duplicate_ids:
                reasons.append("duplicate_symbol")
            if signal_id in outside_allowlist_ids:
                reasons.append("outside_allowlist")
            affected.append(
                {
                    "signal_id": signal_id,
                    "symbol": asset.symbol,
                    "provider_name": signal.provider_name,
                    "signal_status": signal.signal_status.value,
                    "scan_ts": signal.scan_ts.isoformat() if signal.scan_ts is not None else None,
                    "signal_score": float(signal.signal_score or 0.0),
                    "reasons": reasons,
                }
            )
        return affected

    def _build_recommendations(
        self,
        *,
        stale_count: int,
        duplicate_count: int,
        outside_allowlist_count: int,
        mutate_supported: bool,
        dry_run: bool,
        apply: bool,
        updated_count: int,
    ) -> list[str]:
        notes: list[str] = []
        if stale_count > 0:
            notes.append(f"{stale_count} stale paper-test candidate(s) detected.")
        if duplicate_count > 0:
            notes.append(f"{duplicate_count} duplicate same-symbol candidate(s) detected.")
        if outside_allowlist_count > 0:
            notes.append(f"{outside_allowlist_count} outside-allowlist candidate(s) detected.")
        if not notes:
            notes.append("Queue hygiene is clean for paper-test candidates.")

        if apply and dry_run:
            notes.append("Apply requested with dry_run=true; no updates performed.")
        if apply and not dry_run and not mutate_supported:
            notes.append("No safe archival status available; returning recommendations only.")
        if apply and not dry_run and mutate_supported:
            notes.append(f"Applied hygiene updates to {updated_count} candidate(s).")

        return notes
