"""Tests for ModelCandidateService and rollback policy (Phase 11)."""
import pytest

from app.services.governance.model_candidate_service import (
    ModelCandidateService,
)


class TestModelCandidateService:
    def setup_method(self):
        self.svc = ModelCandidateService()

    def _register(self, model_type: str = "scoring") -> str:
        record = self.svc.register(
            model_type=model_type,
            metrics={"primary_metric": 0.70, "brier_score": 0.18},
            training_config={"seed": 42},
        )
        return record.candidate_id

    def test_register_creates_pending_record(self):
        cid = self._register()
        record = self.svc.get(cid)
        assert record.status == "pending"
        assert record.model_type == "scoring"

    def test_register_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid model_type"):
            self.svc.register(
                model_type="unknown",
                metrics={"auc": 0.7},
                training_config={},
            )

    def test_register_empty_metrics_raises(self):
        with pytest.raises(ValueError, match="At least one metric"):
            self.svc.register(
                model_type="regime",
                metrics={},
                training_config={},
            )

    def test_approve_changes_status(self):
        cid = self._register()
        record = self.svc.approve(cid)
        assert record.status == "approved"

    def test_approve_non_pending_raises(self):
        cid = self._register()
        self.svc.approve(cid)
        with pytest.raises(ValueError, match="Cannot approve"):
            self.svc.approve(cid)

    def test_reject_changes_status(self):
        cid = self._register()
        record = self.svc.reject(cid, reason="Insufficient improvement")
        assert record.status == "rejected"
        assert "Insufficient" in record.notes

    def test_reject_promoted_raises(self):
        cid = self._register()
        self.svc.approve(cid)
        self.svc.mark_promoted(cid)
        with pytest.raises(ValueError, match="Cannot reject"):
            self.svc.reject(cid)

    def test_mark_promoted_approved_only(self):
        cid = self._register()
        with pytest.raises(ValueError, match="Cannot mark candidate"):
            self.svc.mark_promoted(cid)

    def test_mark_promoted_succeeds_after_approve(self):
        cid = self._register()
        self.svc.approve(cid)
        record = self.svc.mark_promoted(cid)
        assert record.status == "promoted"

    def test_list_by_status_filters_correctly(self):
        cid1 = self._register("regime")
        cid2 = self._register("execution")
        self.svc.approve(cid2)

        pending = self.svc.list_by_status("pending")
        approved = self.svc.list_by_status("approved")
        assert any(r.candidate_id == cid1 for r in pending)
        assert any(r.candidate_id == cid2 for r in approved)

    def test_list_invalid_status_raises(self):
        with pytest.raises(ValueError, match="Invalid status"):
            self.svc.list_by_status("nonsense")

    def test_get_missing_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.svc.get("nonexistent-id")

    def test_all_model_types_register(self):
        for mt in ("regime", "scoring", "execution"):
            cid = self._register(mt)
            record = self.svc.get(cid)
            assert record.model_type == mt
