"""PromptAdaptationService — propose prompt revisions based on outcome history.

Reads PerformanceStats, identifies underperforming setup types, and asks the
LLM to propose a revised signal-engine prompt.  It NEVER modifies existing
PromptVersion rows (Gate 11 compliance); it only returns a proposal dataclass.

The caller (route handler / admin UI) decides whether to apply the proposal
via the `POST /prompt-adaptations/apply` endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.performance_stats_service import (
    PerformanceStatsService,
)

# Threshold below which a setup is considered underperforming
_UNDERPERFORM_WIN_RATE = 0.40
_UNDERPERFORM_MIN_SAMPLES = 20


@dataclass
class PromptAdaptationProposal:
    """Proposed prompt adaptation based on live signal outcome data."""

    setup_type: str
    rationale: str
    proposed_prompt_text: str
    current_win_rate: float
    total_samples: int


class PromptAdaptationService:
    """Identifies underperforming setups and proposes LLM prompt adjustments.

    Parameters
    ----------
    performance_stats_service:
        Service used to read signal outcome aggregates.
    llm_client:
        Optional callable ``(system_prompt, user_prompt) -> str`` used to ask
        the LLM for a revised prompt.  When *None* a no-op stub is used (useful
        for tests and when no LLM key is configured).
    """

    def __init__(
        self,
        performance_stats_service: PerformanceStatsService,
        llm_client=None,
    ) -> None:
        self._stats = performance_stats_service
        self._llm_client = llm_client

    def propose_adaptation(
        self,
        setup_type: str,
        min_samples: int = _UNDERPERFORM_MIN_SAMPLES,
    ) -> PromptAdaptationProposal | None:
        """Return a proposal for *setup_type* if it is underperforming.

        Returns *None* when the setup is performing acceptably or has too few
        samples.
        """
        by_setup = self._stats.win_rate_by_setup(min_samples=min_samples)
        match = next((r for r in by_setup if r.key == setup_type), None)

        if match is None:
            # Check without the sample-size filter in case it is just under threshold
            by_setup_all = self._stats.win_rate_by_setup(min_samples=0)
            match = next((r for r in by_setup_all if r.key == setup_type), None)
            if match is None or match.total < min_samples:
                return None

        if match.win_rate >= _UNDERPERFORM_WIN_RATE:
            return None

        rationale = (
            f"Setup type '{setup_type}' has a win rate of {match.win_rate:.1%} "
            f"over {match.total} samples, which is below the {_UNDERPERFORM_WIN_RATE:.0%} threshold. "
            "A prompt revision is proposed to improve directional accuracy."
        )

        proposed_text = self._ask_llm_for_revision(setup_type, match.win_rate, match.total)

        return PromptAdaptationProposal(
            setup_type=setup_type,
            rationale=rationale,
            proposed_prompt_text=proposed_text,
            current_win_rate=match.win_rate,
            total_samples=match.total,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ask_llm_for_revision(
        self,
        setup_type: str,
        win_rate: float,
        total_samples: int,
    ) -> str:
        """Ask LLM for a revised prompt focusing on the underperforming setup."""
        if self._llm_client is None:
            # Stub — used in tests and when no LLM is configured
            return (
                f"[STUB] Revised prompt for {setup_type}: consider tightening entry criteria "
                f"given {win_rate:.1%} win rate across {total_samples} trades."
            )

        system = (
            "You are an expert algorithmic trading prompt engineer. "
            "Your task is to revise a trading signal prompt section to improve directional accuracy."
        )
        user = (
            f"The '{setup_type}' setup type has a win rate of {win_rate:.1%} over "
            f"{total_samples} historical trades. This is below the 40% minimum threshold.\n\n"
            "Write a revised prompt section (2-5 sentences) that will help the LLM improve "
            f"directional accuracy for the '{setup_type}' setup. Focus on stricter entry "
            "conditions and clearer regime/catalyst requirements."
        )
        return self._llm_client(system, user)
