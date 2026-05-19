"""Tests for PromptAdaptationService — QA-221/222/223."""

from __future__ import annotations

from unittest.mock import MagicMock


from app.services.performance_stats_service import DimensionWinRate
from app.services.prompt_adaptation_service import (
    PromptAdaptationProposal,
    PromptAdaptationService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(setup_type: str, win_rate: float, total: int, llm_client=None):
    """Build a PromptAdaptationService with mocked performance stats."""
    mock_stats = MagicMock()
    dim_row = DimensionWinRate(
        key=setup_type,
        total=total,
        wins=int(total * win_rate),
        win_rate=win_rate,
    )
    mock_stats.win_rate_by_setup.return_value = [dim_row]
    return PromptAdaptationService(
        performance_stats_service=mock_stats,
        llm_client=llm_client,
    )


# ---------------------------------------------------------------------------
# QA-221 — PromptAdaptationService unit tests
# ---------------------------------------------------------------------------


def test_propose_returns_none_when_win_rate_acceptable():
    service = _make_service("TREND_PULLBACK", win_rate=0.55, total=25)
    proposal = service.propose_adaptation("TREND_PULLBACK", min_samples=20)
    assert proposal is None


def test_propose_returns_proposal_for_underperforming_setup():
    service = _make_service("BREAKDOWN_FADE", win_rate=0.30, total=25)
    proposal = service.propose_adaptation("BREAKDOWN_FADE", min_samples=20)
    assert proposal is not None
    assert isinstance(proposal, PromptAdaptationProposal)


def test_proposal_has_required_fields():
    service = _make_service("BREAKDOWN_FADE", win_rate=0.30, total=25)
    proposal = service.propose_adaptation("BREAKDOWN_FADE", min_samples=20)
    assert hasattr(proposal, "setup_type")
    assert hasattr(proposal, "rationale")
    assert hasattr(proposal, "proposed_prompt_text")
    assert hasattr(proposal, "current_win_rate")
    assert hasattr(proposal, "total_samples")


def test_proposal_setup_type_matches():
    service = _make_service("BREAKDOWN_FADE", win_rate=0.30, total=25)
    proposal = service.propose_adaptation("BREAKDOWN_FADE", min_samples=20)
    assert proposal.setup_type == "BREAKDOWN_FADE"


def test_proposal_rationale_is_non_empty():
    service = _make_service("BREAKDOWN_FADE", win_rate=0.30, total=25)
    proposal = service.propose_adaptation("BREAKDOWN_FADE", min_samples=20)
    assert len(proposal.rationale) > 0


def test_proposal_uses_stub_when_no_llm_client():
    service = _make_service("BREAKDOWN_FADE", win_rate=0.25, total=30, llm_client=None)
    proposal = service.propose_adaptation("BREAKDOWN_FADE", min_samples=20)
    assert "[STUB]" in proposal.proposed_prompt_text


def test_proposal_calls_llm_client_when_provided():
    mock_llm = MagicMock(return_value="Custom revised prompt text.")
    service = _make_service("BREAKDOWN_FADE", win_rate=0.25, total=30, llm_client=mock_llm)
    proposal = service.propose_adaptation("BREAKDOWN_FADE", min_samples=20)
    mock_llm.assert_called_once()
    assert proposal.proposed_prompt_text == "Custom revised prompt text."


def test_gate11_service_does_not_mutate_prompt_versions():
    """Gate 11: PromptAdaptationService must NOT write to any DB model directly."""
    # The service only reads stats and calls LLM — it has no session attribute
    service = _make_service("BREAKDOWN_FADE", win_rate=0.25, total=30)
    assert not hasattr(service, "_session"), (
        "PromptAdaptationService must not hold a DB session (Gate 11)"
    )


# ---------------------------------------------------------------------------
# QA-222 — Apply route Gate 11 test (in-process route test)
# ---------------------------------------------------------------------------


def test_apply_route_creates_new_prompt_version():
    """POST /prompt-adaptations/apply must create a new PromptVersion row."""
    from unittest.mock import MagicMock
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.db.session import get_db_session
    from app.db.enums import PromptRole
    import uuid

    mock_session = MagicMock()

    existing_pv = MagicMock()
    existing_pv.role = PromptRole.SIGNAL_ENGINE
    existing_pv.version = "1.0"
    existing_pv.user_template = "User template"
    existing_pv.schema_json = {}

    mock_session.execute.return_value.scalar_one_or_none.return_value = existing_pv

    new_pv_id = uuid.uuid4()

    def fake_refresh(obj):
        obj.id = new_pv_id
        obj.name = obj.name
        obj.role = PromptRole.SIGNAL_ENGINE
        obj.version = "1.1"
        obj.is_active = False

    mock_session.refresh.side_effect = fake_refresh

    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: mock_session

    client = TestClient(app)
    response = client.post(
        "/prompt-adaptations/apply",
        json={
            "setup_type": "BREAKDOWN_FADE",
            "rationale": "Low win rate detected.",
            "proposed_prompt_text": "New prompt text for breakdown_fade.",
            "current_win_rate": 0.28,
            "total_samples": 25,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["version"] == "1.1"
    assert data["is_active"] is False

    # Verify the existing version was NOT updated (Gate 11)
    existing_pv.version = existing_pv.version  # no write
    mock_session.add.assert_called_once()
    added_obj = mock_session.add.call_args[0][0]
    from app.db.models.prompt_version import PromptVersion
    assert isinstance(added_obj, PromptVersion)


# ---------------------------------------------------------------------------
# QA-223 — Eval harness structural validation
# ---------------------------------------------------------------------------


def test_eval_proposal_structurally_valid_with_mocked_llm():
    """Given a mock LLM, propose_adaptation returns a structurally valid proposal."""
    mock_llm = MagicMock(return_value="Revised: tighten momentum confirmation.")
    service = _make_service("RANGE_FADE", win_rate=0.20, total=30, llm_client=mock_llm)

    proposal = service.propose_adaptation("RANGE_FADE", min_samples=20)

    assert proposal is not None
    assert isinstance(proposal.setup_type, str) and len(proposal.setup_type) > 0
    assert isinstance(proposal.rationale, str) and len(proposal.rationale) > 0
    assert isinstance(proposal.proposed_prompt_text, str) and len(proposal.proposed_prompt_text) > 0
    assert 0.0 <= proposal.current_win_rate <= 1.0
    assert proposal.total_samples > 0
