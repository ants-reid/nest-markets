"""SignalGenerationService — thin facade for signal generation only.

This service wraps ``SignalService`` and exposes a clean generation-only
boundary.  By separating generation from scoring:

- ``SignalGenerationService`` is responsible for LLM calls, prompt loading,
  and structured output validation.
- ``ScoringService`` owns composite score computation.
- ``OpportunityRankerService`` orchestrates both for ranking.

Phase 3: delegates directly to the existing ``SignalService``.  Future phases
may swap the underlying implementation without changing callers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.signal_service import SignalInput, SignalOutput, SignalService

if TYPE_CHECKING:
    from app.clients.llm.router import LLMProviderRouter
    from app.prompts.loader import PromptLoader
    from app.prompts.schema_loader import SchemaLoader
    from sqlalchemy.orm import Session


class SignalGenerationService:
    """Facade for signal generation; delegates to SignalService.

    Use this class in new code rather than importing SignalService directly,
    so the generation boundary is explicit and can be swapped in Phase 7+.
    """

    def __init__(
        self,
        router: "LLMProviderRouter",
        prompt_loader: "PromptLoader | None" = None,
        schema_loader: "SchemaLoader | None" = None,
        session: "Session | None" = None,
        performance_stats_service=None,
    ) -> None:
        self._delegate = SignalService(
            router=router,
            prompt_loader=prompt_loader,
            schema_loader=schema_loader,
            session=session,
            performance_stats_service=performance_stats_service,
        )

    async def generate(self, signal_input: SignalInput) -> SignalOutput:
        """Generate and validate a single structured signal."""
        return await self._delegate.generate_signal(signal_input)

    def get_last_prompt_version_id(self):
        return self._delegate.get_last_prompt_version_id()

    def get_last_model_version_id(self):
        return self._delegate.get_last_model_version_id()
