"""MVP signal service using filesystem prompts and provider-agnostic LLM routing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.llm.base import LLMRequest
from app.clients.llm.router import LLMProviderRouter
from app.config import get_settings
from app.db.enums import PromptRole
from app.db.models.model_version import ModelVersion
from app.db.models.prompt_version import PromptVersion
from app.prompts.loader import PromptLoader
from app.prompts.schema_loader import SchemaLoader
from app.services.llm_input_sanitizer import sanitize_dict
from app.services.signal_geometry_validator import validate_payload as validate_signal_geometry

_SYSTEM_PROMPT_PATH = "system/signal_engine_v1.md"
_USER_TEMPLATE_PATH = "user/signal_input_template_v1.md"
_SIGNAL_SCHEMA_PATH = "schemas/signal_schema_v1.json"


@dataclass(frozen=True)
class SignalInput:
    """Input contract for generating a single structured signal."""

    feature_snapshot: dict[str, Any]
    catalyst_context: dict[str, Any]
    asset: str
    timeframe: str
    latest_price: float
    risk_notes: str | None = None


@dataclass(frozen=True)
class SignalOutput:
    """Typed structured signal output validated against schema."""

    asset: str
    timeframe: str
    direction: str
    regime: str
    setup_type: str
    entry_zone: tuple[float, float]
    stop_price: float
    target_price: float
    confidence: float
    horizon_label: str
    catalyst_type: str
    catalyst_score: float
    catalyst_summary: str
    thesis: str
    invalidators: list[str]
    signal_score: float
    should_trade: bool


class SignalService:
    """Generates a signal by loading versioned prompts and calling the active LLM provider."""

    def __init__(
        self,
        router: LLMProviderRouter,
        prompt_loader: PromptLoader | None = None,
        schema_loader: SchemaLoader | None = None,
        session: Session | None = None,
        performance_stats_service=None,
    ) -> None:
        """Initialize service with router and optional filesystem loaders."""
        settings = get_settings()
        self._router = router
        self._prompt_loader = prompt_loader or PromptLoader()
        self._schema_loader = schema_loader or SchemaLoader()
        self._session = session
        self._model_name = settings.openai_model_name
        self._temperature = settings.openai_temperature
        self._last_prompt_version_id = None
        self._last_model_version_id = None
        self._performance_stats_service = performance_stats_service

    async def generate_signal(self, signal_input: SignalInput) -> SignalOutput:
        """Generate and validate a single structured signal output."""
        system_prompt = self._prompt_loader.load_prompt(_SYSTEM_PROMPT_PATH)
        user_template = self._prompt_loader.load_prompt(_USER_TEMPLATE_PATH)
        schema = self._schema_loader.load_schema(_SIGNAL_SCHEMA_PATH)

        user_prompt = self.render_user_prompt(user_template, signal_input)
        request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            model_name=self._model_name,
            temperature=self._temperature,
        )

        provider = self._router.get_provider()
        raw_payload = await provider.generate_structured(request)
        payload = raw_payload.content if hasattr(raw_payload, "content") else raw_payload

        if self._session is not None:
            self._last_prompt_version_id = self._resolve_prompt_version_id()
            self._last_model_version_id = self._persist_model_version(
                provider_name=provider.__class__.__name__.replace("Provider", "").lower(),
                provider_model=getattr(raw_payload, "model", None) or getattr(provider, "model", self._model_name),
                prompt_version_id=self._last_prompt_version_id,
            )

        Draft202012Validator(schema).validate(payload)
        # MH-151 — reject signals whose price geometry is unsafe (inverted entry
        # zone, stop on wrong side of entry, NaN/inf, zero-distance, etc.).
        # Raises SignalGeometryError before any downstream caller can act.
        validate_signal_geometry(payload)
        return self._to_signal_output(payload)

    def get_last_prompt_version_id(self):
        return self._last_prompt_version_id

    def get_last_model_version_id(self):
        return self._last_model_version_id

    def render_user_prompt(self, template: str, signal_input: SignalInput) -> str:
        """Render the user prompt from template and provided signal input values.

        MH-149: ``feature_snapshot``, ``catalyst_context``, and ``risk_notes``
        are sanitized before serialization so untrusted upstream text cannot
        inject control chars, oversized payloads, or markdown fences into the
        LLM user prompt. Sanitization is a no-op for clean inputs.
        """
        safe_feature_snapshot = sanitize_dict(signal_input.feature_snapshot)
        safe_catalyst_context = sanitize_dict(signal_input.catalyst_context)
        safe_risk_notes = (
            sanitize_dict({"_": signal_input.risk_notes})["_"]
            if signal_input.risk_notes is not None
            else None
        )
        rendered = template.format(
            asset=signal_input.asset,
            timeframe=signal_input.timeframe,
            regime_hint=safe_feature_snapshot.get("regime_preclassification", "unknown"),
            latest_price=signal_input.latest_price,
            feature_snapshot_json=json.dumps(safe_feature_snapshot, sort_keys=True),
            catalyst_context_json=json.dumps(safe_catalyst_context, sort_keys=True),
            risk_notes=safe_risk_notes or "none",
        )
        perf_block = self._build_performance_context_block()
        if perf_block:
            rendered = rendered + "\n\n" + perf_block
        return rendered

    def _build_performance_context_block(self, min_samples: int = 10) -> str:
        """Return a structured performance context block, or empty string if not enough data."""
        if self._performance_stats_service is None:
            return ""
        try:
            stats = self._performance_stats_service.overall_stats(min_samples=min_samples)
        except Exception:
            return ""
        if stats.total_trades < min_samples:
            return ""

        lines: list[str] = ["## Historical Performance Context"]
        lines.append(
            f"Overall win rate: {stats.overall_win_rate:.1%} "
            f"({stats.total_wins}/{stats.total_trades} trades)"
        )
        if stats.by_setup:
            lines.append("Setup win rates:")
            for r in stats.by_setup:
                lines.append(f"  - {r.key}: {r.win_rate:.1%} ({r.total} samples)")
        if stats.by_regime:
            lines.append("Regime win rates:")
            for r in stats.by_regime:
                lines.append(f"  - {r.key}: {r.win_rate:.1%} ({r.total} samples)")
        return "\n".join(lines)

    def _to_signal_output(self, payload: dict[str, Any]) -> SignalOutput:
        """Convert validated payload dictionary into typed service output."""
        entry_zone_raw = payload["entry_zone"]
        entry_zone = (float(entry_zone_raw[0]), float(entry_zone_raw[1]))

        return SignalOutput(
            asset=str(payload["asset"]),
            timeframe=str(payload["timeframe"]),
            direction=str(payload["direction"]),
            regime=str(payload["regime"]),
            setup_type=str(payload["setup_type"]),
            entry_zone=entry_zone,
            stop_price=float(payload["stop_price"]),
            target_price=float(payload["target_price"]),
            confidence=float(payload["confidence"]),
            horizon_label=str(payload["horizon_label"]),
            catalyst_type=str(payload["catalyst_type"]),
            catalyst_score=float(payload["catalyst_score"]),
            catalyst_summary=str(payload["catalyst_summary"]),
            thesis=str(payload["thesis"]),
            invalidators=[str(item) for item in payload["invalidators"]],
            signal_score=float(payload["signal_score"]),
            should_trade=bool(payload["should_trade"]),
        )

    def _resolve_prompt_version_id(self):
        if self._session is None:
            return None

        row = (
            self._session.execute(
                select(PromptVersion)
                .where(PromptVersion.role == PromptRole.SIGNAL_ENGINE)
                .order_by(PromptVersion.created_at.desc())
            )
            .scalars()
            .first()
        )
        return row.id if row is not None else None

    def _persist_model_version(self, *, provider_name: str, provider_model: str, prompt_version_id):
        if self._session is None:
            return None

        row = ModelVersion(
            provider_name=provider_name,
            provider=provider_name,
            model_name=provider_model,
            alias_name=self._model_name,
            temperature=self._temperature,
            supports_structured_output=True,
            is_active=True,
            notes=(
                f"prompt_version_id={prompt_version_id}; system_prompt={_SYSTEM_PROMPT_PATH}; "
                f"user_template={_USER_TEMPLATE_PATH}; schema={_SIGNAL_SCHEMA_PATH}"
            ),
        )
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return row.id


__all__ = ["SignalInput", "SignalOutput", "SignalService", "ValidationError"]
