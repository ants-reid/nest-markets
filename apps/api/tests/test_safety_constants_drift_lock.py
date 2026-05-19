"""Cycle 55 — Service-layer safety constants pin.

Pins the numeric thresholds that the risk gate evaluates. Cycle 54
pinned the gate FUNCTION NAMES; this lock pins the actual NUMBERS
those functions compare against.

Why this matters:
  * Drift in ``_MAX_OPEN_POSITIONS_MVP`` silently changes how many
    open positions trigger the ``max_open_positions_exceeded`` block.
  * Drift in ``RiskProfile.min_confidence`` silently changes the
    approval bar for new signals.
  * Drift in ``RiskProfile.max_daily_drawdown_pct`` silently changes
    the daily kill-switch trigger.
  * A reviewer reading a one-line numeric change in ``risk_service.py``
    or ``risk_profile_service.py`` cannot tell whether the change was
    intentional. This pin forces the reviewer to ALSO update the lock,
    making the safety implication explicit.

Drift-lock notes:
    * Pure additive test; no production code change.
    * Auto-trading gate ``assert_auto_trading_allowed()`` unchanged.
    * Does not call the risk service — pure module-attribute inspection.

How to update this pin:
  When intentionally tuning a threshold, update the pinned value in
  this file in the SAME PR. The deliberate bump IS the safety review.
"""

from __future__ import annotations

from app.services import risk_service
from app.services.risk_profile_service import RiskDefaults, RiskProfile


# ── _MAX_OPEN_POSITIONS_MVP ─────────────────────────────────────────────
# Hard cap on simultaneously-open positions in MVP. 6 is the deliberate
# choice. Drift to a higher number silently widens portfolio exposure;
# drift to lower silently rejects approvals that would previously pass.
EXPECTED_MAX_OPEN_POSITIONS_MVP: int = 6


# ── RiskProfile dataclass defaults ──────────────────────────────────────
# These are the in-process defaults applied when no DB-stored profile is
# present. Drift here changes the silent fall-back behaviour for any
# caller that bypasses the DB profile lookup.
EXPECTED_RISK_PROFILE_DEFAULTS: dict[str, float | int] = {
    "min_confidence": 0.62,
    "min_signal_score": 68.0,
    "max_spread_bps": 25.0,
    "max_daily_drawdown_pct": 2.0,
    "cooldown_after_losses_min": 180,
    "max_correlated_exposure": 2,
    "capital_cap": 100000.0,
    "max_risk_per_trade_pct": 0.50,
}


# ── RiskDefaults dataclass (hard-coded MVP defaults) ────────────────────
# The MVP-default thresholds returned by RiskProfileService.get_defaults().
# Splits FX/equity spread caps separately. Drift in either silently
# relaxes the spread gate for that asset class.
EXPECTED_RISK_DEFAULTS_SEED: dict[str, float] = {
    "min_confidence": 0.62,
    "min_signal_score": 68.0,
    "max_spread_bps_fx": 12.0,
    "max_spread_bps_equity": 25.0,
    "max_daily_drawdown_pct": 2.0,
    "cooldown_after_3_losses_min": 180.0,
    "max_open_positions": 6.0,
    "max_correlated_bucket_exposure": 2.0,
    "max_risk_per_trade_pct": 0.50,
}


def test_max_open_positions_mvp_pinned():
    actual = risk_service._MAX_OPEN_POSITIONS_MVP
    assert actual == EXPECTED_MAX_OPEN_POSITIONS_MVP, (
        f"risk_service._MAX_OPEN_POSITIONS_MVP drifted: "
        f"expected {EXPECTED_MAX_OPEN_POSITIONS_MVP}, got {actual}. "
        "This is the hard cap on simultaneously-open positions. "
        "Raising it silently widens portfolio exposure beyond what "
        "the MVP risk model assumes."
    )


def test_risk_profile_dataclass_defaults_pinned():
    """Defaults of the in-process RiskProfile dataclass."""
    # Construct with no args to exercise the field defaults.
    profile = RiskProfile()
    for name, expected in EXPECTED_RISK_PROFILE_DEFAULTS.items():
        actual = getattr(profile, name)
        assert actual == expected, (
            f"RiskProfile.{name} default drifted: "
            f"expected {expected!r}, got {actual!r}. "
            "This default applies whenever a caller bypasses the DB "
            "profile lookup — drift silently changes the fall-back "
            "approval bar."
        )


def test_risk_defaults_pinned():
    """Defaults of the hard-coded MVP RiskDefaults dataclass."""
    seed = RiskDefaults()
    for name, expected in EXPECTED_RISK_DEFAULTS_SEED.items():
        actual = getattr(seed, name)
        assert actual == expected, (
            f"RiskDefaults.{name} drifted: "
            f"expected {expected!r}, got {actual!r}. "
            "This is the hard-coded MVP threshold returned by "
            "RiskProfileService.get_defaults() — drift silently changes "
            "the gate for any caller that uses the defaults."
        )


def test_risk_profile_defaults_are_sane():
    """Defensive sanity gates that catch obvious wrong-direction drift
    even if the pin itself was updated incorrectly:
      * confidence threshold must be in (0, 1]
      * signal-score threshold must be in (0, 100]
      * spread cap must be > 0
      * drawdown cap must be > 0 and < 100
      * correlated exposure must be a positive int
    """
    profile = RiskProfile()
    assert 0.0 < profile.min_confidence <= 1.0, (
        f"RiskProfile.min_confidence={profile.min_confidence} is outside (0, 1]. "
        "A confidence threshold of 0 silently approves every signal."
    )
    assert 0.0 < profile.min_signal_score <= 100.0, (
        f"RiskProfile.min_signal_score={profile.min_signal_score} is outside (0, 100]."
    )
    assert profile.max_spread_bps > 0, (
        f"RiskProfile.max_spread_bps={profile.max_spread_bps} must be > 0."
    )
    assert 0.0 < profile.max_daily_drawdown_pct < 100.0, (
        f"RiskProfile.max_daily_drawdown_pct={profile.max_daily_drawdown_pct} "
        "is outside (0, 100). A drawdown cap of 0 silently halts trading "
        "on any loss; a cap of 100+ silently disables the kill switch."
    )
    assert isinstance(profile.max_correlated_exposure, int), (
        "RiskProfile.max_correlated_exposure must remain int-typed."
    )
    assert profile.max_correlated_exposure > 0, (
        f"RiskProfile.max_correlated_exposure={profile.max_correlated_exposure} "
        "must be > 0 (a value of 0 silently blocks every correlated trade)."
    )


def test_max_open_positions_mvp_is_positive_int():
    """Defensive: must remain a positive int. Drift to 0 silently
    blocks every approval; drift to a string silently raises TypeError
    inside the gate which callers might swallow."""
    val = risk_service._MAX_OPEN_POSITIONS_MVP
    assert isinstance(val, int), (
        f"_MAX_OPEN_POSITIONS_MVP must remain int, got {type(val).__name__}."
    )
    assert val > 0, (
        f"_MAX_OPEN_POSITIONS_MVP={val} must be > 0; a value of 0 silently "
        "blocks every approval."
    )
