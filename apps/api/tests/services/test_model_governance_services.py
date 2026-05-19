"""Tests for model governance services — QA-310 through QA-320."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.db.models.model_version import ModelVersion
from app.services.governance.model_audit_service import ModelAuditService
from app.services.governance.model_registry_service import ModelRegistryService
from app.services.governance.model_promotion_service import ModelPromotionService
from app.services.governance.model_rollback_service import ModelRollbackService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_version(**kwargs) -> MagicMock:
    defaults = dict(
        id=uuid4(),
        provider_name="openai",
        provider="openai",
        model_name="gpt-4o",
        alias_name=None,
        temperature=0.7,
        top_p=None,
        max_output_tokens=None,
        reasoning_level=None,
        supports_structured_output=True,
        is_active=False,
        notes=None,
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=ModelVersion)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# ModelAuditService
# ---------------------------------------------------------------------------


def test_audit_log_create() -> None:
    session = MagicMock()
    svc = ModelAuditService(session)
    version = _make_version()
    svc.log_create(version)
    session.add.assert_called_once()
    entry = session.add.call_args[0][0]
    assert entry.event_type == "model_governance.create"
    assert entry.entity_type == "model_version"


def test_audit_log_promote() -> None:
    session = MagicMock()
    svc = ModelAuditService(session)
    version = _make_version()
    prev_id = str(uuid4())
    svc.log_promote(version, previous_id=prev_id)
    entry = session.add.call_args[0][0]
    assert entry.event_type == "model_governance.promote"
    assert entry.payload_json["previous_active_id"] == prev_id


def test_audit_log_rollback() -> None:
    session = MagicMock()
    svc = ModelAuditService(session)
    version = _make_version()
    svc.log_rollback(version, rolled_back_from_id="some-uuid")
    entry = session.add.call_args[0][0]
    assert entry.event_type == "model_governance.rollback"
    assert entry.payload_json["rolled_back_from_id"] == "some-uuid"


# ---------------------------------------------------------------------------
# ModelRegistryService
# ---------------------------------------------------------------------------


def test_registry_create_adds_row() -> None:
    session = MagicMock()
    created_version = _make_version(is_active=False)
    session.flush = MagicMock()
    session.refresh = MagicMock()

    # Make session.add capture the version and make it retrievable
    def fake_flush():
        pass
    def fake_refresh(obj):
        obj.id = created_version.id

    session.flush.side_effect = fake_flush
    session.refresh.side_effect = fake_refresh

    audit = MagicMock(spec=ModelAuditService)
    svc = ModelRegistryService(session=session, audit_service=audit)

    # Patch to return a real-ish object
    with MagicMock() as _:
        svc.create(provider_name="openai", model_name="gpt-4o")
        session.add.assert_called_once()
        audit.log_create.assert_called_once()


def test_registry_deactivate_sets_flag() -> None:
    session = MagicMock()
    version_id = uuid4()
    version = _make_version(id=version_id, is_active=True)
    session.get.return_value = version
    audit = MagicMock(spec=ModelAuditService)

    svc = ModelRegistryService(session=session, audit_service=audit)
    svc.deactivate(version_id)

    assert version.is_active is False
    audit.log_deactivate.assert_called_once_with(version)


def test_registry_deactivate_raises_on_missing() -> None:
    session = MagicMock()
    session.get.return_value = None

    svc = ModelRegistryService(session=session)
    with pytest.raises(ValueError, match="not found"):
        svc.deactivate(uuid4())


def test_registry_update_raises_on_missing() -> None:
    session = MagicMock()
    session.get.return_value = None

    svc = ModelRegistryService(session=session)
    with pytest.raises(ValueError, match="not found"):
        svc.update(uuid4(), notes="new notes")


# ---------------------------------------------------------------------------
# ModelPromotionService
# ---------------------------------------------------------------------------


def test_promotion_sets_is_active_true() -> None:
    session = MagicMock()
    candidate_id = uuid4()
    candidate = _make_version(id=candidate_id, is_active=False)
    session.get.return_value = candidate

    # No existing active version
    session.execute.return_value.scalars.return_value.first.return_value = None

    audit = MagicMock(spec=ModelAuditService)
    svc = ModelPromotionService(session=session, audit_service=audit)
    result = svc.promote(candidate_id)

    assert result.is_active is True
    audit.log_promote.assert_called_once_with(candidate, previous_id=None)


def test_promotion_deactivates_previous() -> None:
    session = MagicMock()
    candidate_id = uuid4()
    previous_id = uuid4()

    candidate = _make_version(id=candidate_id, is_active=False)
    previous = _make_version(id=previous_id, is_active=True)

    session.get.return_value = candidate
    session.execute.return_value.scalars.return_value.first.return_value = previous

    audit = MagicMock(spec=ModelAuditService)
    svc = ModelPromotionService(session=session, audit_service=audit)
    svc.promote(candidate_id)

    assert previous.is_active is False
    assert candidate.is_active is True
    audit.log_promote.assert_called_once_with(candidate, previous_id=str(previous_id))


def test_promotion_raises_on_missing_version() -> None:
    session = MagicMock()
    session.get.return_value = None

    svc = ModelPromotionService(session=session)
    with pytest.raises(ValueError, match="not found"):
        svc.promote(uuid4())


# ---------------------------------------------------------------------------
# ModelRollbackService
# ---------------------------------------------------------------------------


def test_rollback_raises_when_no_active_version() -> None:
    session = MagicMock()
    session.execute.return_value.scalars.return_value.first.return_value = None

    svc = ModelRollbackService(session=session)
    with pytest.raises(ValueError, match="No active model version"):
        svc.rollback()


def test_rollback_raises_when_no_audit_log() -> None:

    session = MagicMock()
    current = _make_version(is_active=True)

    # First execute → active version; second execute → no audit log
    execute_results = [
        MagicMock(**{"scalars.return_value.first.return_value": current}),
        MagicMock(**{"scalars.return_value.first.return_value": None}),
    ]
    session.execute.side_effect = execute_results

    svc = ModelRollbackService(session=session)
    with pytest.raises(ValueError, match="No promotion audit record"):
        svc.rollback()


def test_rollback_restores_previous_version() -> None:

    session = MagicMock()
    current_id = uuid4()
    previous_id = uuid4()

    current = _make_version(id=current_id, is_active=True)
    previous = _make_version(id=previous_id, is_active=False)

    audit_log = MagicMock()
    audit_log.payload_json = {"previous_active_id": str(previous_id)}
    audit_log.entity_id = current_id

    # execute calls:
    # 1. find current active → current
    # 2. find promote log → audit_log
    execute_results = [
        MagicMock(**{"scalars.return_value.first.return_value": current}),
        MagicMock(**{"scalars.return_value.first.return_value": audit_log}),
    ]
    session.execute.side_effect = execute_results
    session.get.return_value = previous

    audit_svc = MagicMock(spec=ModelAuditService)
    svc = ModelRollbackService(session=session, audit_service=audit_svc)
    result = svc.rollback()

    assert current.is_active is False
    assert previous.is_active is True
    assert result is previous
    audit_svc.log_rollback.assert_called_once()
