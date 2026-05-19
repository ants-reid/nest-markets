"""ModelCandidateService — manage scoring model candidates before promotion.

A candidate is a trained model that has passed walk-forward validation and
is awaiting human or automated promotion approval.  This service provides
lifecycle management for candidate entries tied to the ScoreModelRegistry
DB table.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class CandidateRecord:
    """In-memory representation of a score model candidate."""

    candidate_id: str
    model_type: str
    metrics: dict[str, float]
    training_config: dict[str, Any]
    status: str  # "pending" | "approved" | "rejected" | "promoted"
    notes: str = ""


class ModelCandidateService:
    """
    Manages score model candidates pending promotion review.

    In production this persists records to the ScoreModelRegistry table.
    This stub uses an in-memory dict so that governance pipeline tests
    run without a database.
    """

    VALID_STATUSES = {"pending", "approved", "rejected", "promoted"}
    VALID_MODEL_TYPES = {"regime", "scoring", "execution"}

    def __init__(self) -> None:
        self._store: dict[str, CandidateRecord] = {}

    # ------------------------------------------------------------------

    def register(
        self,
        model_type: str,
        metrics: dict[str, float],
        training_config: dict[str, Any],
        notes: str = "",
    ) -> CandidateRecord:
        """
        Register a new candidate for governance review.

        Args:
            model_type: One of ``regime``, ``scoring``, ``execution``.
            metrics: Evaluation metrics (e.g. ``{"auc": 0.70}``).
            training_config: Config dict used to produce the model.
            notes: Optional human-readable notes.

        Returns:
            CandidateRecord with status ``"pending"``.

        Raises:
            ValueError: If model_type is not recognised or metrics empty.
        """
        if model_type not in self.VALID_MODEL_TYPES:
            raise ValueError(
                f"Invalid model_type '{model_type}'. "
                f"Valid: {sorted(self.VALID_MODEL_TYPES)}"
            )
        if not metrics:
            raise ValueError("At least one metric is required")

        candidate_id = str(uuid.uuid4())
        record = CandidateRecord(
            candidate_id=candidate_id,
            model_type=model_type,
            metrics=metrics,
            training_config=training_config,
            status="pending",
            notes=notes,
        )
        self._store[candidate_id] = record
        return record

    def get(self, candidate_id: str) -> CandidateRecord:
        """Return a candidate by ID, raising ValueError if not found."""
        if candidate_id not in self._store:
            raise ValueError(f"Candidate '{candidate_id}' not found")
        return self._store[candidate_id]

    def list_by_status(self, status: str) -> list[CandidateRecord]:
        """Return all candidates with the given status."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Valid: {sorted(self.VALID_STATUSES)}")
        return [r for r in self._store.values() if r.status == status]

    def approve(self, candidate_id: str) -> CandidateRecord:
        """Mark a pending candidate as approved for promotion."""
        record = self.get(candidate_id)
        if record.status != "pending":
            raise ValueError(
                f"Cannot approve candidate '{candidate_id}' with status '{record.status}'"
            )
        record.status = "approved"
        return record

    def reject(self, candidate_id: str, reason: str = "") -> CandidateRecord:
        """Mark a pending candidate as rejected."""
        record = self.get(candidate_id)
        if record.status not in ("pending", "approved"):
            raise ValueError(
                f"Cannot reject candidate '{candidate_id}' with status '{record.status}'"
            )
        record.status = "rejected"
        if reason:
            record.notes = reason
        return record

    def mark_promoted(self, candidate_id: str) -> CandidateRecord:
        """Mark an approved candidate as promoted after successful activation."""
        record = self.get(candidate_id)
        if record.status != "approved":
            raise ValueError(
                f"Cannot mark candidate '{candidate_id}' as promoted; "
                f"current status is '{record.status}'"
            )
        record.status = "promoted"
        return record
