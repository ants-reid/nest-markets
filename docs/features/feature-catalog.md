# Feature Catalog

## Technical Features

| Feature | Module | Description | Unit |
|---------|--------|-------------|------|
| `roc_5` | `momentum` | 5-day rate-of-change | fraction |
| `roc_21` | `momentum` | 21-day rate-of-change | fraction |
| `roc_63` | `momentum` | 63-day rate-of-change (quarter) | fraction |
| `atr_14` | `volatility` | 14-day Average True Range | price |
| `realised_vol_21` | `volatility` | 21-day annualised realised volatility | fraction |
| `pivot_high_5` | `levels` | Highest high in 5-bar window | price |
| `pivot_low_5` | `levels` | Lowest low in 5-bar window | price |
| `vwap` | `levels` | Volume-weighted average price | price |
| `distance_from_52w_high` | `levels` | % distance from 52-week high | fraction |
| `is_compressed` | `patterns` | Range compression flag | bool |
| `is_breakout` | `patterns` | 20-day breakout flag | bool |
| `relative_volume` | `volume` | Latest volume / 20-day avg volume | ratio |

## Cross-Sectional Features

| Feature | Module | Description |
|---------|--------|-------------|
| `sector_strength` | `sector_strength` | Mean return of sector peers |
| `ad_ratio` | `breadth` | Advance/decline ratio for the universe |
| `breadth_thrust` | `breadth` | Zweig Breadth Thrust (10-day EMA) |
| `percentile_rank` | `relative_rank` | Return percentile vs universe (0–100) |
| `z_score_rank` | `relative_rank` | Return z-score vs universe |

## Macro Features

| Feature | Module | Description |
|---------|--------|-------------|
| `yield_curve_slope` | `yield_curve` | 10Y minus 2Y spread |
| `is_inverted` | `yield_curve` | Inverted yield curve flag |
| `fed_funds_regime` | `liquidity` | Fed Funds rate classification |
| `real_rate` | `liquidity` | Nominal rate minus CPI inflation |
| `vix_regime` | `volatility` | VIX bucket (low_vol/normal/elevated/crisis) |
| `vix_percentile` | `volatility` | VIX percentile vs history |

## News Features

| Feature | Module | Description |
|---------|--------|-------------|
| `mean_sentiment` | `sentiment` | Mean sentiment score of recent articles |
| `sentiment_regime` | `sentiment` | Qualitative sentiment bucket |
| `days_to_earnings` | `event_proximity` | Calendar days to next earnings |
| `event_proximity_bucket` | `event_proximity` | Proximity classification |

## Execution Features

| Feature | Module | Description |
|---------|--------|-------------|
| `absolute_spread` | `spread` | Bid/ask spread in price units |
| `relative_spread` | `spread` | Spread as % of mid-price |
| `spread_regime` | `spread` | tight / normal / wide |
| `liquidity_score` | `liquidity_score` | 0–1 composite liquidity score |
