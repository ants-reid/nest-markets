Generate one structured signal object from the input below.

Asset: {asset}
Timeframe: {timeframe}
Market regime hint: {regime_hint}
Latest price: {latest_price}
Feature snapshot JSON: {feature_snapshot_json}
Catalyst context JSON: {catalyst_context_json}
Risk notes: {risk_notes}

Requirements:
- Follow the system instructions.
- Match the schema exactly.
- Be conservative under uncertainty.
- Use only the supplied inputs.
- Prefer no trade over a weak trade.
- Price structure matters more than narrative.
- News is a catalyst layer, not a standalone trigger.
- If no trade: direction must be "flat", setup_type must be "none", should_trade must be false.
- If no trade: entry_zone must be [0, 0], stop_price must be 0, target_price must be 0.
- Return JSON only.
