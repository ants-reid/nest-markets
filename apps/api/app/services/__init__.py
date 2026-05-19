"""Services package.

Exports are loaded lazily to avoid importing unrelated dependencies at module import
time (for example during targeted unit tests).
"""

from importlib import import_module
from typing import Any

__all__ = [
    "FeatureAdapterRequest",
    "FeatureAdapterService",
    "BarInput",
    "QuoteInput",
    "FeatureInput",
    "FeatureSnapshotPayload",
    "build_feature_snapshot",
    "SignalService",
    "SignalInput",
    "SignalOutput",
    "RiskService",
    "RiskInput",
    "RiskOutput",
    "RiskProfileService",
    "RiskDefaults",
    "ExecutionModeService",
    "ExecutionRoute",
    "PaperExecutionService",
    "ApprovalService",
    "LiveExecutionService",
    "LiveExecutionDisabledError",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "FeatureAdapterRequest": ("app.services.feature_adapter_service", "FeatureAdapterRequest"),
    "FeatureAdapterService": ("app.services.feature_adapter_service", "FeatureAdapterService"),
    "BarInput": ("app.services.feature_service", "BarInput"),
    "QuoteInput": ("app.services.feature_service", "QuoteInput"),
    "FeatureInput": ("app.services.feature_service", "FeatureInput"),
    "FeatureSnapshotPayload": ("app.services.feature_service", "FeatureSnapshotPayload"),
    "build_feature_snapshot": ("app.services.feature_service", "build_feature_snapshot"),
    "SignalService": ("app.services.signal_service", "SignalService"),
    "SignalInput": ("app.services.signal_service", "SignalInput"),
    "SignalOutput": ("app.services.signal_service", "SignalOutput"),
    "RiskService": ("app.services.risk_service", "RiskService"),
    "RiskInput": ("app.services.risk_service", "RiskInput"),
    "RiskOutput": ("app.services.risk_service", "RiskOutput"),
    "RiskProfileService": ("app.services.risk_profile_service", "RiskProfileService"),
    "RiskDefaults": ("app.services.risk_profile_service", "RiskDefaults"),
    "ExecutionModeService": ("app.services.execution_mode_service", "ExecutionModeService"),
    "ExecutionRoute": ("app.services.execution_mode_service", "ExecutionRoute"),
    "PaperExecutionService": ("app.services.paper_execution_service", "PaperExecutionService"),
    "ApprovalService": ("app.services.approval_service", "ApprovalService"),
    "LiveExecutionService": ("app.services.live_execution_service", "LiveExecutionService"),
    "LiveExecutionDisabledError": (
        "app.services.live_execution_service",
        "LiveExecutionDisabledError",
    ),
}


def __getattr__(name: str) -> Any:
    """Lazily import public service symbols."""
    if name not in _LAZY_IMPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = _LAZY_IMPORTS[name]
    module = import_module(module_name)
    return getattr(module, attribute_name)
