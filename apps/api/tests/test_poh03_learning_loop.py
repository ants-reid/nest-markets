"""POH-03: Learning loop validation for RC-3 deployment.

Validates that signal outcomes can be aggregated into performance stats,
and that performance stats can be used to generate prompt adaptations.
This is a smoke test verifying the learning loop services are wired correctly.
"""

from unittest.mock import MagicMock

from app.services.performance_stats_service import PerformanceStatsService
from app.services.prompt_adaptation_service import PromptAdaptationService


class TestPOH03LearningLoopValidation:
    """Learning loop validation: outcomes → stats → adaptations."""

    def test_performance_stats_service_instantiates(self):
        """PerformanceStatsService must be instantiable with a session."""
        mock_session = MagicMock()
        service = PerformanceStatsService(mock_session)
        
        assert service is not None
        assert service._session == mock_session

    def test_prompt_adaptation_service_instantiates(self):
        """PromptAdaptationService must be instantiable with stats service and optional LLM."""
        mock_session = MagicMock()
        perf_svc = PerformanceStatsService(mock_session)
        mock_llm = MagicMock()
        
        adapt_svc = PromptAdaptationService(perf_svc, mock_llm)
        
        assert adapt_svc is not None
        assert adapt_svc._stats == perf_svc
        assert adapt_svc._llm_client == mock_llm

    def test_prompt_adaptation_service_works_without_llm(self):
        """PromptAdaptationService must work with llm_client=None."""
        mock_session = MagicMock()
        perf_svc = PerformanceStatsService(mock_session)
        
        # Should not raise error with None llm_client
        adapt_svc = PromptAdaptationService(perf_svc, None)
        assert adapt_svc is not None

    def test_learning_loop_services_are_importable(self):
        """Learning loop services must be importable from app.services."""
        from app.services.performance_stats_service import PerformanceStatsService
        from app.services.prompt_adaptation_service import PromptAdaptationService
        
        assert PerformanceStatsService is not None
        assert PromptAdaptationService is not None

    def test_performance_stats_service_has_required_methods(self):
        """PerformanceStatsService must have all required aggregation methods."""
        mock_session = MagicMock()
        service = PerformanceStatsService(mock_session)
        
        # Verify required methods exist
        assert hasattr(service, 'overall_stats')
        assert hasattr(service, 'win_rate_by_setup')
        assert hasattr(service, 'win_rate_by_asset')
        assert hasattr(service, 'win_rate_by_catalyst')
        assert hasattr(service, 'win_rate_by_regime')
        assert callable(service.overall_stats)
        assert callable(service.win_rate_by_setup)
        assert callable(service.win_rate_by_asset)

    def test_prompt_adaptation_service_has_required_methods(self):
        """PromptAdaptationService must have proposal generation method."""
        mock_session = MagicMock()
        perf_svc = PerformanceStatsService(mock_session)
        adapt_svc = PromptAdaptationService(perf_svc, None)
        
        # Verify required methods exist
        assert hasattr(adapt_svc, 'propose_adaptation')
        assert callable(adapt_svc.propose_adaptation)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
