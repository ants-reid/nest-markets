"""Publish a trained candidate model to the model registry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PublishRequest:
    """Request to publish a candidate model."""

    model_type: str  # "regime" | "scoring" | "execution"
    model_id: str
    artifacts: dict[str, Any]
    metrics: dict[str, float]
    training_config: dict[str, Any]
    notes: str = ""


@dataclass
class PublishResult:
    """Result of publishing a candidate model."""

    candidate_id: str
    model_type: str
    status: str  # "published" | "rejected"
    reason: str
    registry_url: str


class CandidateModelPublisher:
    """
    Publishes a trained model as a candidate in the model registry.

    The candidate enters the governance pipeline and must pass promotion
    policy checks before it replaces the active model.
    """

    VALID_MODEL_TYPES = {"regime", "scoring", "execution"}

    def publish(self, request: PublishRequest) -> PublishResult:
        """
        Publish a trained model as a candidate.

        Args:
            request: Publish request containing model artifacts and metrics.

        Returns:
            PublishResult indicating success or rejection.

        Raises:
            ValueError: If model_type is invalid or required metrics missing.
        """
        if request.model_type not in self.VALID_MODEL_TYPES:
            raise ValueError(
                f"Invalid model_type '{request.model_type}'. "
                f"Must be one of: {sorted(self.VALID_MODEL_TYPES)}"
            )

        if not request.metrics:
            raise ValueError("Candidate model must include at least one metric")

        if not request.artifacts:
            raise ValueError("Candidate model must include at least one artifact")

        # Stub — real implementation writes to DB registry + blob storage
        candidate_id = f"candidate-{request.model_type}-{request.model_id}"

        return PublishResult(
            candidate_id=candidate_id,
            model_type=request.model_type,
            status="published",
            reason="Candidate registered successfully",
            registry_url=f"/models/{candidate_id}",
        )
