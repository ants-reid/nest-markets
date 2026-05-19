from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.enums import PromptRole
from app.db.models.model_version import ModelVersion
from app.db.models.prompt_version import PromptVersion
from app.services.signal_service import SignalInput, SignalService


def test_generate_signal_persists_model_version_when_session_present():
    session = MagicMock(spec=Session)

    prompt_version = PromptVersion(
        name="signal_engine_v1.md",
        role=PromptRole.SIGNAL_ENGINE,
        version="v1",
        system_prompt="system",
        user_template="user",
        schema_json={},
        is_active=True,
    )
    prompt_version.id = uuid4()

    def _execute(stmt):
        result = MagicMock()
        result.scalars.return_value.first.return_value = prompt_version
        return result

    session.execute.side_effect = _execute

    def _refresh(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()

    session.refresh.side_effect = _refresh

    provider = MagicMock()
    provider.model = "gpt-4.1-mini"
    provider.generate_structured = AsyncMock(
        return_value={
            "asset": "EURUSD",
            "timeframe": "1h",
            "direction": "long",
            "regime": "trend",
            "setup_type": "trend_pullback",
            "entry_zone": [1.0810, 1.0820],
            "stop_price": 1.0790,
            "target_price": 1.0850,
            "confidence": 0.75,
            "horizon_label": "1_3_days",
            "catalyst_type": "macro",
            "catalyst_score": 0.65,
            "catalyst_summary": "summary",
            "thesis": "thesis",
            "invalidators": ["x"],
            "signal_score": 78.5,
            "should_trade": True,
        }
    )

    router = MagicMock()
    router.get_provider.return_value = provider
    service = SignalService(router=router, session=session)

    result = asyncio.run(
        service.generate_signal(
            SignalInput(
                feature_snapshot={"regime_preclassification": "trend"},
                catalyst_context={},
                asset="EURUSD",
                timeframe="1h",
                latest_price=1.0815,
            )
        )
    )

    assert result.asset == "EURUSD"
    added_models = [type(call.args[0]) for call in session.add.call_args_list]
    assert ModelVersion in added_models
    assert service.get_last_prompt_version_id() == prompt_version.id
    assert service.get_last_model_version_id() is not None
