import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


def _load_catalyst_schema() -> dict:
    schema_path = Path(__file__).resolve().parents[1] / "prompts" / "schemas" / "catalyst_schema_v1.json"
    return json.loads(schema_path.read_text())


def test_catalyst_schema_accepts_valid_payload() -> None:
    schema = _load_catalyst_schema()
    payload = {
        "affected_assets": ["XAUUSD", "DXY"],
        "catalyst_type": "macro",
        "directional_bias": "mixed",
        "freshness_score": 0.82,
        "relevance_score": 0.77,
        "priced_in_risk": 0.38,
        "time_horizon": "days",
        "summary": "Policy commentary shifted rate expectations over the next few sessions.",
    }

    Draft202012Validator(schema).validate(payload)


def test_catalyst_schema_rejects_invalid_payload() -> None:
    schema = _load_catalyst_schema()
    payload = {
        "affected_assets": ["XAUUSD"],
        "catalyst_type": "regulatory",
        "directional_bias": "bullish",
        "freshness_score": 0.82,
        "relevance_score": 0.77,
        "priced_in_risk": 0.38,
        "time_horizon": "days",
        "summary": "Invalid catalyst type should fail enum validation.",
    }

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(payload)
