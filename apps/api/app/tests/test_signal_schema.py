import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


def _load_signal_schema() -> dict:
    schema_path = Path(__file__).resolve().parents[1] / "prompts" / "schemas" / "signal_schema_v1.json"
    return json.loads(schema_path.read_text())


def test_signal_schema_accepts_valid_trade_payload() -> None:
    schema = _load_signal_schema()
    payload = {
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

    Draft202012Validator(schema).validate(payload)


def test_signal_schema_accepts_valid_no_trade_payload() -> None:
    schema = _load_signal_schema()
    payload = {
        "asset": "SPY",
        "timeframe": "4h",
        "direction": "flat",
        "regime": "risk_off",
        "setup_type": "none",
        "entry_zone": [0, 0],
        "stop_price": 0,
        "target_price": 0,
        "confidence": 0.31,
        "horizon_label": "intraday",
        "catalyst_type": "none",
        "catalyst_score": 0.0,
        "catalyst_summary": "No clear catalyst with acceptable structure quality.",
        "thesis": "Conflicting signals and poor structure quality.",
        "invalidators": ["N/A - no trade"],
        "signal_score": 41,
        "should_trade": False,
    }

    Draft202012Validator(schema).validate(payload)


def test_signal_schema_rejects_invalid_payload() -> None:
    schema = _load_signal_schema()
    payload = {
        "asset": "EURUSD",
        "timeframe": "5m",
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
        "invalidators": ["1h close below 1.0780"],
        "signal_score": 76,
        "should_trade": True,
    }

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(payload)
