# Risk Rules

## MVP risk defaults
- max_open_positions = 6
- max_risk_per_trade_pct = 0.50
- max_daily_drawdown_pct = 2.00
- max_correlated_bucket_exposure = 2
- min_confidence = 0.62
- min_signal_score = 68
- max_spread_bps_fx = 12
- max_spread_bps_equity = 25
- cooldown_after_3_losses_min = 180

## Core blocking logic
Block trade if:
- should_trade is false
- direction is flat
- confidence below threshold
- signal_score below threshold
- spread too wide
- market quality flag is bad
- daily drawdown exceeded
- correlation exposure exceeded
- cooldown active
- kill switch active
- mode policy forbids execution

## Operating principle
The same signal and risk process must apply to:
- paper mode
- confirm-before-trade mode
- auto mode

Only the final routing changes.
