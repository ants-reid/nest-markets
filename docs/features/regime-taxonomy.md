# Regime Taxonomy

Market Hunter uses six regime labels.  The `RegimeClassifier` assigns one label
per day based on a rules-based heuristic using VIX, price momentum, market
breadth, and yield-curve slope.

## Labels

| Regime | Code | Conditions | Typical Behaviour |
|--------|------|------------|-------------------|
| Risk On | `risk_on` | Low VIX (<14), positive momentum, broad advance | Trend following, long bias |
| Risk Off | `risk_off` | Negative breadth OR inverted yield curve | Defensive, reduced size |
| High Vol | `high_vol` | VIX ≥ 30 | Minimum size, cash preference |
| Low Vol | `low_vol` | VIX ≤ 14, mixed signals | Normal operation, wider targets |
| Chop | `chop` | Flat momentum, no clear signal | Tighter stops, reduced frequency |
| Trend | `trend` | SPY ROC-21 > +3% | Momentum continuation preferred |

## Transitions

Regime transitions are validated by `RegimeValidationService`.  Some transitions
are flagged as implausible and trigger a data-quality warning:

- `low_vol → high_vol` — would require VIX to jump from <14 to ≥30 in a single day.

## Classification Logic

```
if vix >= 30:              → high_vol
elif vix <= 14:
    if momentum > 0 and AD > 1.1: → risk_on
    else:                  → low_vol
elif spy_roc_21 > 3%:      → trend
elif |spy_roc_21| < 1%:    → chop
elif AD < 0.9 or curve < 0: → risk_off
else:                      → chop
```

## Usage

```python
from apps.learning.services.regime.regime_classifier import RegimeClassifier, RegimeInput

classifier = RegimeClassifier()
result = classifier.classify(RegimeInput(vix=28, spy_roc_21=0.01, advance_decline_ratio=0.95, yield_curve_slope=-0.1))
print(result.regime)  # "risk_off"
```
