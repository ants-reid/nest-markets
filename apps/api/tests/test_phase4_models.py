"""Tests for Phase 4 DB model imports and basic structure — QA-400."""

from __future__ import annotations



def test_all_phase4_models_importable() -> None:
    """All Phase 4 models must import without errors."""


def test_phase4_models_have_correct_tablenames() -> None:
    from app.db.models.feature_definitions import FeatureDefinition
    from app.db.models.filing_events import FilingEvent
    from app.db.models.fundamental_snapshots import FundamentalSnapshot
    from app.db.models.macro_observations import MacroObservation
    from app.db.models.macro_series import MacroSeries
    from app.db.models.market_regimes import MarketRegime
    from app.db.models.missed_opportunity_labels import MissedOpportunityLabel
    from app.db.models.news_items import NewsItem
    from app.db.models.news_symbol_links import NewsSymbolLink
    from app.db.models.opportunity_outcomes import OpportunityOutcome
    from app.db.models.score_model_evaluations import ScoreModelEvaluation
    from app.db.models.score_model_parameters import ScoreModelParameters
    from app.db.models.score_model_promotions import ScoreModelPromotion
    from app.db.models.score_model_registry import ScoreModelRegistry
    from app.db.models.score_model_rollbacks import ScoreModelRollback
    from app.db.models.scored_opportunities import ScoredOpportunity

    assert FeatureDefinition.__tablename__ == "feature_definitions"
    assert FilingEvent.__tablename__ == "filing_events"
    assert FundamentalSnapshot.__tablename__ == "fundamental_snapshots"
    assert MacroObservation.__tablename__ == "macro_observations"
    assert MacroSeries.__tablename__ == "macro_series"
    assert MarketRegime.__tablename__ == "market_regimes"
    assert MissedOpportunityLabel.__tablename__ == "missed_opportunity_labels"
    assert NewsItem.__tablename__ == "news_items"
    assert NewsSymbolLink.__tablename__ == "news_symbol_links"
    assert OpportunityOutcome.__tablename__ == "opportunity_outcomes"
    assert ScoreModelEvaluation.__tablename__ == "score_model_evaluations"
    assert ScoreModelParameters.__tablename__ == "score_model_parameters"
    assert ScoreModelPromotion.__tablename__ == "score_model_promotions"
    assert ScoreModelRegistry.__tablename__ == "score_model_registry"
    assert ScoreModelRollback.__tablename__ == "score_model_rollbacks"
    assert ScoredOpportunity.__tablename__ == "scored_opportunities"


def test_phase4_enums_importable() -> None:
    from app.db.enums import (
        ExecutionOutcomeStatus,
        FilingEventType,
        MarketRegimeType,
        ModelRegistryStatus,
        PromotionType,
        RollbackTrigger,
    )
    assert ExecutionOutcomeStatus.EXECUTED == "executed"
    assert FilingEventType.EARNINGS == "earnings"
    assert MarketRegimeType.TREND == "trend"
    assert ModelRegistryStatus.CANDIDATE == "candidate"
    assert PromotionType.CANDIDATE_TO_ACTIVE == "candidate_to_active"
    assert RollbackTrigger.MANUAL == "manual"


def test_models_init_exports_phase4() -> None:
    from app.db.models import (
        ScoreModelRegistry,
        ScoredOpportunity,
    )
    # All should be importable from the package level
    assert ScoreModelRegistry.__tablename__ == "score_model_registry"
    assert ScoredOpportunity.__tablename__ == "scored_opportunities"
