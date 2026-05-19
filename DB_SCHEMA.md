# Database Schema: Market Hunter MVP Expansion

This document defines all new database tables added in Phases 4-13.

**Existing tables** (from Phase 0) are assumed and not repeated here. See `apps/api/app/db/models/` for current schema.

---

## PHASE 4: GOVERNANCE AND MODEL TABLES

### score_model_registry

Primary model registry. Tracks all trained models and their metadata.

```sql
CREATE TABLE score_model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version_number INT NOT NULL,
    strategy_bucket VARCHAR(100) NOT NULL,
    asset_class VARCHAR(50) NOT NULL,
    description TEXT,
    training_date TIMESTAMPTZ NOT NULL,
    trained_by VARCHAR(255),
    status ENUM ('candidate', 'active', 'archived', 'failed') NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    promoted_at TIMESTAMPTZ,
    promoted_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(strategy_bucket, asset_class, version_number)
);
```

**Key fields:**
- `strategy_bucket`: Bucketing strategy (e.g., "long_equity", "short_tech")
- `status`: Model lifecycle (candidate → active, active → archived, or failed)
- `is_active`: True if this is the currently active model for the bucket
- `promoted_by`: User or system that promoted the model

---

### score_model_versions

Model artifact storage. Each row is one trained model file/artifact.

```sql
CREATE TABLE score_model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_registry_id UUID NOT NULL REFERENCES score_model_registry(id),
    model_artifact_path VARCHAR(512) NOT NULL,
    artifact_hash VARCHAR(64) NOT NULL,
    framework VARCHAR(50),
    framework_version VARCHAR(50),
    hyperparameters JSONB,
    training_config JSONB,
    validation_metrics JSONB,
    sample_size INT,
    training_regimes TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(model_registry_id, artifact_hash)
);
```

**Key fields:**
- `model_artifact_path`: Path to model file (S3, local, etc.)
- `hyperparameters`: Saved model params as JSON
- `validation_metrics`: Metrics from validation (accuracy, calibration, etc.)
- `training_regimes`: Array of regime tags present in training data

---

### score_model_parameters

Configurable scoring parameters per bucket and regime.

```sql
CREATE TABLE score_model_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_registry_id UUID NOT NULL REFERENCES score_model_registry(id),
    parameter_name VARCHAR(255) NOT NULL,
    parameter_value NUMERIC,
    min_value NUMERIC,
    max_value NUMERIC,
    parameter_type VARCHAR(50),
    description TEXT,
    regime_tag VARCHAR(100),
    effective_date TIMESTAMPTZ DEFAULT NOW(),
    deprecated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(model_registry_id, parameter_name, regime_tag)
);
```

---

### score_model_evaluations

Validation results from training pipeline runs.

```sql
CREATE TABLE score_model_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_registry_id UUID NOT NULL REFERENCES score_model_registry(id),
    evaluation_run_id VARCHAR(255) NOT NULL,
    evaluation_date TIMESTAMPTZ NOT NULL,
    validation_strategy VARCHAR(100),
    metric_name VARCHAR(100),
    metric_value NUMERIC,
    metric_details JSONB,
    passed_gates BOOLEAN,
    gate_failures TEXT[],
    evaluated_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(model_registry_id, evaluation_run_id, metric_name)
);
```

**Key fields:**
- `validation_strategy`: "walk_forward", "cross_validation", etc.
- `passed_gates`: True if all sample size and performance gates passed
- `gate_failures`: Array of gate names that failed

---

### score_model_promotions

Promotion audit trail.

```sql
CREATE TABLE score_model_promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_model_id UUID REFERENCES score_model_registry(id),
    to_model_id UUID NOT NULL REFERENCES score_model_registry(id),
    promotion_type ENUM ('candidate_to_active', 'active_to_active') NOT NULL,
    promoted_at TIMESTAMPTZ DEFAULT NOW(),
    promoted_by VARCHAR(255),
    approval_notes TEXT,
    rollback_eligible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### score_model_rollbacks

Rollback audit trail (automatic or manual).

```sql
CREATE TABLE score_model_rollbacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_model_id UUID NOT NULL REFERENCES score_model_registry(id),
    to_model_id UUID NOT NULL REFERENCES score_model_registry(id),
    rollback_reason VARCHAR(255),
    rollback_trigger ENUM ('automatic', 'manual', 'performance_degradation') NOT NULL,
    triggered_by VARCHAR(255),
    rollback_timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## PHASE 4: REGIME AND FEATURE TABLES

### market_regimes

Current and historical market regime classifications.

```sql
CREATE TABLE market_regimes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regime_name VARCHAR(100) NOT NULL,
    regime_description TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    characteristics JSONB,
    volatility_percentile NUMERIC,
    trend_direction VARCHAR(50),
    liquidity_condition VARCHAR(50),
    regime_type ENUM ('risk_on', 'risk_off', 'high_vol', 'low_vol', 'chop', 'trend') NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(regime_name, start_date)
);
```

---

### feature_definitions

Metadata about all engineered features.

```sql
CREATE TABLE feature_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_name VARCHAR(255) NOT NULL UNIQUE,
    feature_category VARCHAR(100),
    description TEXT,
    computation_rule TEXT,
    source_data_types TEXT[],
    pit_safe BOOLEAN,
    lookback_bars INT,
    default_value NUMERIC,
    normalization_rule VARCHAR(255),
    na_handling VARCHAR(100),
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Key fields:**
- `pit_safe`: True if safe to use in point-in-time queries
- `lookback_bars`: How many bars required for computation
- `normalization_rule`: How to normalize the feature (z-score, min-max, etc.)

---

### feature_snapshots

Point-in-time feature vectors for each signal/opportunity.

```sql
CREATE TABLE feature_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID REFERENCES signal(id),
    opportunity_id UUID REFERENCES scored_opportunities(id),
    snapshot_timestamp TIMESTAMPTZ NOT NULL,
    asset_id UUID NOT NULL REFERENCES asset(id),
    regime_tag VARCHAR(100),
    feature_values JSONB NOT NULL,
    feature_version INT DEFAULT 1,
    computation_timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(signal_id, snapshot_timestamp),
    UNIQUE(opportunity_id, snapshot_timestamp)
);
```

**Key fields:**
- `feature_values`: Dictionary of {feature_name: value}
- `feature_version`: Version of feature definitions used
- `computation_timestamp`: When features were computed

---

## PHASE 4: OPPORTUNITY AND OUTCOME TABLES

### scored_opportunities

All signals after scoring.

```sql
CREATE TABLE scored_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES signal(id),
    asset_id UUID NOT NULL REFERENCES asset(id),
    score NUMERIC NOT NULL,
    score_components JSONB,
    model_version_id UUID REFERENCES score_model_registry(id),
    regime_tag VARCHAR(100),
    bucket_assignment VARCHAR(255),
    explanation TEXT,
    expected_move_pct NUMERIC,
    expected_drawdown_pct NUMERIC,
    do_not_trade_probability NUMERIC,
    scored_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Key fields:**
- `score_components`: {signal_score, confidence, catalyst, historical_wr, ...}
- `bucket_assignment`: Which bucket this opportunity belongs to
- `explanation`: Human-readable score breakdown

---

### opportunity_outcomes

Execution outcome labels for learning loop.

```sql
CREATE TABLE opportunity_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID NOT NULL REFERENCES scored_opportunities(id),
    signal_id UUID NOT NULL REFERENCES signal(id),
    execution_status ENUM ('executed', 'blocked', 'missed', 'skipped') NOT NULL,
    outcome_category VARCHAR(100),
    entry_price NUMERIC,
    exit_price NUMERIC,
    realized_pnl NUMERIC,
    realized_pnl_pct NUMERIC,
    expected_pnl_pct NUMERIC,
    slippage_pct NUMERIC,
    mfe_pct NUMERIC,
    mae_pct NUMERIC,
    r_multiple NUMERIC,
    exit_reason VARCHAR(100),
    execution_quality_score NUMERIC,
    outcome_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### missed_opportunity_labels

Hypothetical outcomes for opportunities NOT executed.

```sql
CREATE TABLE missed_opportunity_labels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID NOT NULL REFERENCES scored_opportunities(id),
    signal_id UUID NOT NULL REFERENCES signal(id),
    reason_not_executed VARCHAR(255),
    hypothetical_entry NUMERIC,
    hypothetical_exit NUMERIC,
    hypothetical_pnl_pct NUMERIC,
    hypothetical_drawdown NUMERIC,
    actual_market_move_pct NUMERIC,
    opportunity_value_label VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Key fields:**
- `opportunity_value_label`: "missed_winner", "avoided_loser", "neutral", etc.

---

## PHASE 5: NEWS AND EVENTS TABLES

### news_items

News articles and headlines.

```sql
CREATE TABLE news_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(512),
    headline TEXT NOT NULL,
    summary TEXT,
    full_text TEXT,
    source VARCHAR(100),
    published_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    sentiment_score NUMERIC,
    urgency_score NUMERIC,
    url VARCHAR(512),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(external_id, source)
);
```

---

### news_symbol_links

Many-to-many: news items → symbols.

```sql
CREATE TABLE news_symbol_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    news_item_id UUID NOT NULL REFERENCES news_items(id),
    asset_id UUID NOT NULL REFERENCES asset(id),
    relevance_score NUMERIC,
    mention_type VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(news_item_id, asset_id)
);
```

---

### filing_events

SEC filings and earnings events.

```sql
CREATE TABLE filing_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES asset(id),
    event_type ENUM ('earnings', '10-k', '10-q', '8-k', 'proxy', 'other') NOT NULL,
    event_date DATE NOT NULL,
    filing_url VARCHAR(512),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(asset_id, event_type, event_date)
);
```

---

## PHASE 5: FUNDAMENTALS AND MACRO TABLES

### fundamental_snapshots

Company fundamentals at point in time.

```sql
CREATE TABLE fundamental_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES asset(id),
    snapshot_date DATE NOT NULL,
    pe_ratio NUMERIC,
    price_to_book NUMERIC,
    debt_to_equity NUMERIC,
    current_ratio NUMERIC,
    roa NUMERIC,
    roe NUMERIC,
    gross_margin NUMERIC,
    net_margin NUMERIC,
    dividend_yield NUMERIC,
    free_cash_flow NUMERIC,
    revenue NUMERIC,
    earnings NUMERIC,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(asset_id, snapshot_date)
);
```

---

### macro_series

Economic time series metadata (CPI, yields, unemployment, VIX, etc.).

```sql
CREATE TABLE macro_series (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    series_code VARCHAR(100) UNIQUE NOT NULL,
    series_name VARCHAR(255) NOT NULL,
    description TEXT,
    units VARCHAR(50),
    frequency VARCHAR(20),
    source VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### macro_observations

Macro data points.

```sql
CREATE TABLE macro_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    macro_series_id UUID NOT NULL REFERENCES macro_series(id),
    observation_date DATE NOT NULL,
    observation_value NUMERIC NOT NULL,
    observation_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(macro_series_id, observation_date)
);
```

---

## PHASE 7: FEATURE AND REGIME SNAPSHOTS

### feature_regime_snapshots

Regime classification + features at a point in time.

```sql
CREATE TABLE feature_regime_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID NOT NULL REFERENCES asset(id),
    snapshot_timestamp TIMESTAMPTZ NOT NULL,
    regime_classification VARCHAR(100),
    regime_probability NUMERIC,
    feature_vector JSONB,
    regime_model_version VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(asset_id, snapshot_timestamp)
);
```

---

## MIGRATIONS

### Alembic Migration Files

Create migrations in `apps/api/alembic/versions/` with proper dependency ordering:

```
[timestamp]_001_add_model_governance_tables.py
  - score_model_registry
  - score_model_versions
  - score_model_parameters
  - score_model_evaluations
  - score_model_promotions
  - score_model_rollbacks

[timestamp]_002_add_regime_feature_tables.py
  - market_regimes
  - feature_definitions
  - feature_snapshots
  - feature_regime_snapshots

[timestamp]_003_add_opportunity_learning_tables.py
  - scored_opportunities
  - opportunity_outcomes
  - missed_opportunity_labels

[timestamp]_004_add_news_fundamentals_tables.py
  - news_items
  - news_symbol_links
  - filing_events
  - fundamental_snapshots

[timestamp]_005_add_macro_tables.py
  - macro_series
  - macro_observations

[timestamp]_006_add_governance_config_seed_data.py
  - Insert default scoring configs
  - Insert default risk profiles
  - Insert default execution modes
```

---

## Key Constraints and Indexes

### Indexes (for performance)

```sql
CREATE INDEX idx_score_model_registry_status ON score_model_registry(status);
CREATE INDEX idx_score_model_registry_is_active ON score_model_registry(is_active);
CREATE INDEX idx_scored_opportunities_signal_id ON scored_opportunities(signal_id);
CREATE INDEX idx_opportunity_outcomes_opportunity_id ON opportunity_outcomes(opportunity_id);
CREATE INDEX idx_news_items_published_at ON news_items(published_at);
CREATE INDEX idx_macro_observations_date ON macro_observations(observation_date);
CREATE INDEX idx_feature_snapshots_signal_id ON feature_snapshots(signal_id);
CREATE INDEX idx_market_regimes_start_date ON market_regimes(start_date);
```

### Referential Integrity

All foreign keys enforce:
- ON DELETE: CASCADE (most cases)
- ON UPDATE: CASCADE
- ON DELETE: RESTRICT (score_model_registry, to prevent accidental deletions)

---

## Seed Data

### Default Scoring Config

```python
# apps/api/alembic/versions/[hash]_06_seed_default_configs.py

INSERT INTO score_model_registry (
    name, version_number, strategy_bucket, asset_class, description, status
) VALUES
    ('baseline_long_equities_v1', 1, 'long_equities', 'EQUITY', 
     'Initial scoring model for long equity strategies', 'active'),
    ('baseline_short_equities_v1', 1, 'short_equities', 'EQUITY',
     'Initial scoring model for short equity strategies', 'active');

INSERT INTO score_model_parameters (
    model_registry_id, parameter_name, parameter_value, min_value, max_value
) VALUES
    (model1_id, 'weight_signal_score', 0.40, 0.2, 0.6),
    (model1_id, 'weight_confidence', 0.30, 0.1, 0.5),
    (model1_id, 'weight_catalyst', 0.10, 0.0, 0.3),
    (model1_id, 'weight_hist_wr', 0.20, 0.0, 0.4);
```

---

## Testing Notes

All new tables require:
1. **Initialization tests:** Table exists with correct schema
2. **CRUD tests:** Insert, read, update, delete operations
3. **Constraint tests:** Foreign keys, uniqueness constraints
4. **Migration tests:** Migration runs forward and backward
5. **Point-in-time tests:** Historical queries return correct data

---

## Related Files

- Migration generation: `apps/api/alembic/`
- Model definitions: `apps/api/app/db/models/`
- Seed data: `apps/api/alembic/versions/`
- Persistence services: `apps/api/app/services/persistence/`

---

**For complete file-by-file implementation, see FILE_MANIFEST.md (Phases 4-13).**

