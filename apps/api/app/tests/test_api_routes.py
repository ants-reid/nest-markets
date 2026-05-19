from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_mock_generate_signal_route_returns_safe_flat_signal() -> None:
    response = client.post(
        "/signals/mock-generate",
        json={
            "asset": "EURUSD",
            "timeframe": "1h",
            "latest_price": 1.0821,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset"] == "EURUSD"
    assert payload["direction"] == "flat"
    assert payload["should_trade"] is False


def test_risk_evaluate_route_returns_blocked_decision_for_low_confidence() -> None:
    response = client.post(
        "/risk/evaluate",
        json={
            "signal": {
                "asset": "EURUSD",
                "timeframe": "1h",
                "direction": "long",
                "regime": "trend",
                "setup_type": "trend_pullback",
                "entry_zone": [1.081, 1.082],
                "stop_price": 1.078,
                "target_price": 1.088,
                "confidence": 0.2,
                "horizon_label": "1_3_days",
                "catalyst_type": "macro",
                "catalyst_score": 0.6,
                "catalyst_summary": "Macro tailwind",
                "thesis": "Structure supports continuation",
                "invalidators": ["Break below structure"],
                "signal_score": 75,
                "should_trade": True
            },
            "risk_context": {
                "spread_bps": 10.0,
                "daily_drawdown_pct": 1.0,
                "consecutive_losses": 1,
                "minutes_since_last_loss": 240,
                "correlated_exposure_count": 1,
                "market_quality_flag": True,
                "account_equity": 50000.0,
                "requested_execution_mode": "paper"
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is False
    assert "confidence_below_threshold" in payload["blocked_reasons"]
    assert payload["selected_execution_mode"] == "blocked"
