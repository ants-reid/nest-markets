import asyncio
import json
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

from app.services.signal_service import SignalInput, SignalService


class _FakeProvider:
    def __init__(self, payload: dict):
        self._payload = payload
        self.last_request = None

    async def generate_structured(self, request):
        self.last_request = request
        return self._payload


class _FakeRouter:
    def __init__(self, provider: _FakeProvider):
        self._provider = provider

    def get_provider(self):
        return self._provider


class _SpyPromptLoader:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.calls: list[str] = []

    def load_prompt(self, relative_path: str) -> str:
        self.calls.append(relative_path)
        return (self.base_dir / relative_path).read_text(encoding="utf-8")


class _SpySchemaLoader:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.calls: list[str] = []

    def load_schema(self, relative_path: str) -> dict:
        self.calls.append(relative_path)
        return json.loads((self.base_dir / relative_path).read_text(encoding="utf-8"))


def _valid_payload() -> dict:
    return {
        "asset": "EURUSD",
        "timeframe": "1h",
        "direction": "long",
        "regime": "trend",
        "setup_type": "trend_pullback",
        "entry_zone": [1.0810, 1.0820],
        "stop_price": 1.0780,
        "target_price": 1.0880,
        "confidence": 0.74,
        "horizon_label": "1_3_days",
        "catalyst_type": "macro",
        "catalyst_score": 0.63,
        "catalyst_summary": "USD data softened relative to expectations.",
        "thesis": "Higher lows and reclaim of structure support continuation.",
        "invalidators": ["1h close below 1.0780", "break of prior swing low"],
        "signal_score": 76,
        "should_trade": True,
    }


def test_generate_signal_loads_expected_files_and_renders_prompt() -> None:
    prompts_dir = Path(__file__).resolve().parents[1] / "prompts"

    provider = _FakeProvider(_valid_payload())
    router = _FakeRouter(provider)
    prompt_loader = _SpyPromptLoader(prompts_dir)
    schema_loader = _SpySchemaLoader(prompts_dir)

    service = SignalService(router=router, prompt_loader=prompt_loader, schema_loader=schema_loader)
    signal_input = SignalInput(
        feature_snapshot={"regime_preclassification": "trend", "ema_fast": 101.2},
        catalyst_context={"headline": "CPI lower than expected"},
        asset="EURUSD",
        timeframe="1h",
        latest_price=1.0821,
        risk_notes="No major event in next hour",
    )

    result = asyncio.run(service.generate_signal(signal_input))

    assert prompt_loader.calls == ["system/signal_engine_v1.md", "user/signal_input_template_v1.md"]
    assert schema_loader.calls == ["schemas/signal_schema_v1.json"]

    assert provider.last_request is not None
    user_prompt = provider.last_request.user_prompt
    assert "EURUSD" in user_prompt
    assert "1h" in user_prompt
    assert "1.0821" in user_prompt
    assert "CPI lower than expected" in user_prompt

    assert result.asset == "EURUSD"
    assert result.should_trade is True
    assert result.entry_zone == (1.081, 1.082)


def test_generate_signal_raises_for_invalid_payload() -> None:
    prompts_dir = Path(__file__).resolve().parents[1] / "prompts"

    invalid_payload = _valid_payload()
    invalid_payload["timeframe"] = "5m"

    provider = _FakeProvider(invalid_payload)
    router = _FakeRouter(provider)
    prompt_loader = _SpyPromptLoader(prompts_dir)
    schema_loader = _SpySchemaLoader(prompts_dir)

    service = SignalService(router=router, prompt_loader=prompt_loader, schema_loader=schema_loader)
    signal_input = SignalInput(
        feature_snapshot={"regime_preclassification": "trend"},
        catalyst_context={"headline": "None"},
        asset="EURUSD",
        timeframe="1h",
        latest_price=1.0821,
    )

    with pytest.raises(ValidationError):
        asyncio.run(service.generate_signal(signal_input))
