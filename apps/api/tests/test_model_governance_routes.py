"""Tests for model governance routes — Phase 11 routes (POST /governance/promote, rollback)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.models.model_version import ModelVersion
from app.db.session import get_db_session
from app.main import app


def _make_version(**kwargs) -> MagicMock:
    defaults = dict(
        id=uuid.uuid4(),
        provider_name="openai",
        provider="openai",
        model_name="gpt-4o",
        alias_name=None,
        temperature=0.7,
        top_p=None,
        max_output_tokens=None,
        reasoning_level=None,
        supports_structured_output=True,
        is_active=True,
        notes=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=ModelVersion)
    for k, v in defaults.items():
        setattr(obj, k, v)
    obj.model_validate = MagicMock(return_value=obj)
    return obj


@pytest.fixture()
def client():
    db_mock = MagicMock()
    app.dependency_overrides[get_db_session] = lambda: db_mock
    yield TestClient(app), db_mock
    app.dependency_overrides.clear()


class TestGovernancePromoteRoute:
    def test_promote_returns_200(self, client):
        test_client, db_mock = client
        version = _make_version(is_active=True)
        version_id = version.id

        with patch(
            "app.api.routes.governance.ModelPromotionService"
        ) as MockPromotion:
            mock_promo = MagicMock()
            mock_promo.promote.return_value = version
            MockPromotion.return_value = mock_promo

            resp = test_client.post(
                "/governance/promote",
                json={"model_version_id": str(version_id)},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "promote"
        assert data["is_active"] is True

    def test_promote_not_found_returns_404(self, client):
        test_client, db_mock = client

        with patch(
            "app.api.routes.governance.ModelPromotionService"
        ) as MockPromotion:
            mock_promo = MagicMock()
            mock_promo.promote.side_effect = ValueError("not found")
            MockPromotion.return_value = mock_promo

            resp = test_client.post(
                "/governance/promote",
                json={"model_version_id": str(uuid.uuid4())},
            )

        assert resp.status_code == 404

    def test_promote_invalid_uuid_returns_422(self, client):
        test_client, _ = client
        resp = test_client.post(
            "/governance/promote",
            json={"model_version_id": "not-a-uuid"},
        )
        assert resp.status_code == 422


class TestGovernanceRollbackRoute:
    def test_rollback_returns_200(self, client):
        test_client, db_mock = client
        version = _make_version(is_active=True)

        with patch(
            "app.api.routes.governance.ModelRollbackService"
        ) as MockRollback:
            mock_rb = MagicMock()
            mock_rb.rollback.return_value = version
            MockRollback.return_value = mock_rb

            resp = test_client.post("/governance/rollback")

        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "rollback"

    def test_rollback_no_active_returns_400(self, client):
        test_client, db_mock = client

        with patch(
            "app.api.routes.governance.ModelRollbackService"
        ) as MockRollback:
            mock_rb = MagicMock()
            mock_rb.rollback.side_effect = ValueError("No active model")
            MockRollback.return_value = mock_rb

            resp = test_client.post("/governance/rollback")

        assert resp.status_code == 400


class TestModelsRoute:
    def test_get_models_returns_200(self, client):
        test_client, db_mock = client

        with patch(
            "app.api.routes.models.ModelRegistryService"
        ) as MockRegistry:
            mock_reg = MagicMock()
            mock_reg.get_all.return_value = []
            MockRegistry.return_value = mock_reg

            resp = test_client.get("/models")

        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] == 0

    def test_get_active_model_404_when_none(self, client):
        test_client, db_mock = client

        with patch(
            "app.api.routes.models.ModelRegistryService"
        ) as MockRegistry:
            mock_reg = MagicMock()
            mock_reg.get_active.return_value = None
            MockRegistry.return_value = mock_reg

            resp = test_client.get("/models/active")

        assert resp.status_code == 404
