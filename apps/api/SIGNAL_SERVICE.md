# Signal Service (Phase 5)

## Overview

Phase 5 implements the **AI signal generation service** - the critical orchestration point between market features (Phase 3) and the LLM layer (Phase 4).

This service:
- **Proposes only** - Generates trading ideas, doesn't make decisions
- **Orchestrates** - Coordinates features, prompts, and LLM calls
- **Validates** - Ensures output matches expected schema
- **Persists** - Stores signals for approval and execution workflows
- **Logs everything** - Fully auditable for compliance

## Architecture

```
Market Features (Phase 3)
    ↓
[Signal Service] ← Orchestrates signal generation
    ├─ Load active prompt
    ├─ Assemble context (features + macro + news)
    ├─ Call LLM provider
    ├─ Validate output
    └─ Persist signal
    ↓
Signal DB Record
    ↓
[Risk Layer] → Validates against risk rules (Phase 6)
    ↓
[Execution] → Places paper/live orders (Phase 7)
```

## Components

### SignalInput

Input data structure for signal generation:

```python
@dataclass
class SignalInput:
    asset_id: UUID              # Asset to analyze
    asset_symbol: str           # Ticker (e.g., 'AAPL')
    current_price: float        # Current price
    features: dict[str, Any]    # From Phase 3 feature service
    timestamp: datetime         # Signal timestamp

    # Optional context
    macro_context: Optional[dict[str, Any]] = None  # Fed rate, sentiment, etc.
    recent_news: Optional[list[dict]] = None        # Recent headlines
```

### SignalOutput

Result from signal generation:

```python
@dataclass
class SignalOutput:
    signal_id: UUID             # Persisted signal ID
    asset_id: UUID              # Asset analyzed
    direction: str              # "long", "short", "flat"
    confidence: float           # 0-1 confidence score
    catalyst: Optional[str]     # Primary reason
    reasoning: Optional[str]    # Detailed explanation
    structured_output: dict     # Full LLM output
    prompt_version_id: UUID     # Prompt version used
```

### SignalService

Main service class orchestrating signal generation:

```python
from app.services import SignalService, SignalInput, SignalOutput

service = SignalService(
    router=llm_router,      # From LLM layer (Phase 4)
    session=db_session      # For prompt and signal persistence
)

# Generate signal
result = await service.generate_signal(signal_input)
# result is a SignalOutput with generated signal
```

## Usage Example

```python
from datetime import datetime
from uuid import UUID
from app.services import SignalService, SignalInput
from app.clients.llm import LLMProviderRouter
from app.config import Settings
from app.db.session import SessionLocal

# Initialize
settings = Settings()
router = LLMProviderRouter(settings)
session = SessionLocal()
service = SignalService(router=router, session=session)

# Prepare input
signal_input = SignalInput(
    asset_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
    asset_symbol="AAPL",
    current_price=150.25,
    features={
        "sma_20": 148.0,
        "sma_50": 147.0,
        "sma_200": 145.0,
        "rsi_14": 65.0,
        "atr_14": 2.5,
        "volatility": 0.015,
        "trend_direction": "up",
        "trend_strength": 0.8,
        "market_quality": "good",
        "spread_bps": 1.0,
    },
    timestamp=datetime.utcnow(),
    macro_context={
        "fed_rate": 5.5,
        "market_sentiment": "bullish",
    },
    recent_news=[
        {
            "headline": "Strong earnings beat",
            "sentiment": "positive",
        }
    ]
)

# Generate signal
result = await service.generate_signal(signal_input)

# Use result
print(f"Signal: {result.direction} with {result.confidence*100:.0f}% confidence")
print(f"Catalyst: {result.catalyst}")
print(f"Stored as Signal {result.signal_id}")
```

## Responsibilities

### ✅ What This Service Does

1. **Load Active Prompt**
   - Queries database for active "signal_engine" prompt
   - Validates prompt has required fields
   - Logs any errors

2. **Assemble Context**
   - Builds consistent context dict from features
   - Adds macro context (interest rates, sentiment, etc.)
   - Summarizes recent news
   - Ready for template rendering

3. **Render User Prompt**
   - Uses PromptLoader helper
   - Renders template with variables
   - Validates all variables provided

4. **Load Schema**
   - Parses JSON schema from prompt
   - Validates schema structure
   - Used for LLM generation and response validation

5. **Call LLM**
   - Gets provider from router
   - Creates LLMRequest with prompts and schema
   - Handles async generation
   - Captures token usage

6. **Validate Output**
   - Checks required fields present
   - Validates direction enum (long/short/flat)
   - Validates confidence bounds (0-1)
   - Type checking on response

7. **Persist Signal**
   - Creates Signal database record
   - Stores structured output as JSON
   - Stores reasoning and catalyst
   - Marks initial state as "pending"

8. **Return Result**
   - Structured SignalOutput with all data
   - Ready for risk layer (Phase 6)
   - Logging of complete flow

### ❌ What This Service Does NOT Do

- **Apply risk rules** - That's Phase 6 (risk layer)
- **Place orders** - That's Phase 7 (execution layer)
- **Call brokers** - That's execution layer only
- **Route HTTP requests** - That's API layer
- **Train models** - That's evaluation/offline work
- **Make final decisions** - Proposes only

## Design Principles

### 1. Separation of Concerns

```
SignalService
├─ LLMProviderRouter (Phase 4)      # Used for provider selection
├─ PromptLoader (Phase 4 helpers)  # Used for template rendering
├─ SchemaLoader (Phase 4 helpers)  # Used for schema loading
├─ Database queries                # For prompts and signal storage
└─ Logging                         # For audit trail
```

Each responsibility is clearly defined.

### 2. Small, Focused Methods

```python
# Each method has single responsibility
_load_active_prompt()      # Load from DB
_assemble_context()        # Build context dict
_summarize_news()          # Format news for prompt
_validate_signal_output()  # Validate output
_calculate_signal_score()  # Score calculation
_persist_signal()          # DB persistence
_build_output()            # Response building
```

### 3. Type Safety

```python
# Clear input/output types
async def generate_signal(self, signal_input: SignalInput) -> SignalOutput:
    """Generate trading signal from market features."""
    pass

# Dataclass types for structure
@dataclass
class SignalInput:
    asset_id: UUID
    asset_symbol: str
    current_price: float
    features: dict[str, Any]
    ...
```

### 4. Comprehensive Logging

```python
# Log at each step for audit trail
logger.info("signal_generation_start", ...)
logger.debug("active_prompt_loaded", ...)
logger.debug("context_assembled", ...)
logger.debug("llm_response_received", ...)
logger.info("signal_generation_complete", ...)
```

### 5. No Business Logic in Provider

LLMProviderRouter is only for marshalling, not for:
- Risk decisions
- Order logic
- Position sizing
- Trading rules

All these belong in the risk layer (Phase 6).

## Database Schema

### Signal Model

Persists signal generation output:

```
signals
├─ id (UUID)                      # Signal ID
├─ asset_id (UUID, FK)           # Asset analyzed
├─ prompt_version_id (UUID, FK)  # Prompt used
├─ timestamp (DateTime)          # Signal timestamp
├─ direction (String)            # long, short, flat
├─ confidence (Float)            # 0-1 confidence
├─ signal_score (Float)          # Composite score
├─ catalyst (String)             # Primary reason
├─ catalyst_strength (String)    # Catalyst strength
├─ reasoning (Text)              # Detailed explanation
├─ structured_output (JSON)      # Full LLM response
├─ is_actionable (String)        # inactive, pending, approved, rejected
└─ created_at (DateTime)         # Creation timestamp
```

## Configuration

### Environment Variables

None required for signal service - it uses config from Phase 4 (LLM layer).

Settings already include:
- LLM_PROVIDER (openai)
- OPENAI_API_KEY
- OPENAI_MODEL
- OPENAI_TIMEOUT

### Prompt Versioning

Signal service loads prompts from `PromptVersion` table:

```sql
SELECT * FROM prompt_versions
WHERE role = 'signal_engine'
AND is_active = 'active'
LIMIT 1;
```

Each active prompt includes:
- system_prompt - Role and instructions for LLM
- user_template - Template with {variables}
- schema_json - Expected output JSON schema
- notes - Documentation

## Testing

Comprehensive test coverage with mocking:

```bash
# Run all signal service tests
poetry run pytest tests/services/ -v

# Test specific functionality
poetry run pytest tests/services/__init__.py::TestGenerateSignal -v
poetry run pytest tests/services/__init__.py::TestValidateSignalOutput -v
```

### Test Coverage

- **Service initialization**
- **Prompt loading** (success, not found)
- **Context assembly** (basic, with macro, with news)
- **News summarization** (empty, single, multiple)
- **Output validation** (valid, missing fields, invalid direction, bounds)
- **Score calculation** (high, low, bounds)
- **Signal persistence**
- **Complete flow** (success, prompt missing, LLM error, validation error)

### Test Fixtures

- `mock_router` - LLM provider router
- `mock_session` - Database session
- `signal_service` - Service instance
- `mock_prompt_version` - Prompt with schema
- `signal_input` - Input with features
- `llm_response` - LLM output
- `mock_signal` - Persisted signal

## Error Handling

### ValueError

```python
# Raised when required data missing
raise ValueError("No active signal_engine prompt found")
```

### LLMValidationError

```python
# Raised when output doesn't match schema
raise LLMValidationError(f"Missing required fields: {missing_fields}")
raise LLMValidationError(f"Invalid direction: {direction}")
```

### Exception Propagation

LLM errors propagate up:
- Timeout → LLMTimeoutError
- API errors → LLMProviderError
- Invalid JSON → LLMValidationError

All logged before propagation.

## Performance Considerations

### Async Design

All LLM calls are async to avoid blocking:

```python
# Non-blocking LLM call
response = await provider.generate_structured(request)
```

### Database Queries

Minimal queries:
1. Load active prompt (with index on role + is_active)
2. Persist signal (single INSERT)

### Memory Usage

- Signal context dict is built once
- LLM response is validated then used
- No unnecessary data copies

## Auditing

Every signal generation is logged:

```
signal_generation_start
├─ asset_id, asset_symbol, price
active_prompt_loaded
├─ prompt_id, version
context_assembled
├─ asset, macro_context, news_count
llm_response_received
├─ model, tokens used, stop_reason
signal_validation_passed
signal_persisted
├─ signal_id, direction, confidence
signal_generation_complete
```

All logs include:
- Timestamp (from structlog)
- Service name
- Key identifiers
- Success/failure
- Error details if applicable

## Integration with Other Phases

### Phase 3 (Features)

Signal service consumes feature dict:

```python
features = calculate_features(bars, quotes)
signal_input = SignalInput(
    features=features,
    ...
)
```

### Phase 4 (LLM)

Signal service uses LLM provider:

```python
router = LLMProviderRouter(settings)
service = SignalService(router=router, session=session)
```

### Phase 6 (Risk)

Risk layer consumes signal output:

```python
signal = await signal_service.generate_signal(signal_input)
# Risk layer now validates signal against rules
```

## Next Phases

**Phase 6: Risk Validation**
- Apply capital caps
- Check position limits
- Validate spreads
- Mark signal actionable/rejected

**Phase 7: Approval Workflow**
- Create approval requests
- User approval UI
- Scheduled expiration

**Phase 8: Execution**
- Paper execution
- Live execution (if enabled)

## Conservative Defaults

✅ **Signals start as "pending"** - Not automatically actionable
✅ **Schema validation is strict** - All required fields checked
✅ **Type validation** - Direction and confidence bounds verified
✅ **Error logging** - Every error logged for audit
✅ **No assumptions** - Explicit error handling

## Code Example: Full Integration

```python
# Phase 3: Get features
from app.features import calculate_features

bars = [{"open": 150, "high": 151, "low": 149, "close": 150.5, "volume": 1000000}] * 50
features = calculate_features(bars=bars)

# Phase 4: Setup LLM
from app.clients.llm import LLMProviderRouter
from app.config import Settings

settings = Settings()
router = LLMProviderRouter(settings)

# Phase 5: Generate signal
from app.services import SignalService, SignalInput
from app.db.session import SessionLocal
from datetime import datetime
from uuid import uuid4

session = SessionLocal()
service = SignalService(router=router, session=session)

signal_input = SignalInput(
    asset_id=uuid4(),
    asset_symbol="AAPL",
    current_price=150.5,
    features=features,
    timestamp=datetime.utcnow(),
    macro_context={"fed_rate": 5.5}
)

signal = await service.generate_signal(signal_input)
print(f"Generated signal: {signal.direction} at {signal.confidence}")

# Phase 6: Risk validation (next)
# from app.services import RiskService
# approved = await risk_service.validate_signal(signal)
```

## Summary

Signal Service provides:
- ✅ Clean orchestration of features + LLM
- ✅ Type-safe input/output
- ✅ Comprehensive validation
- ✅ Full audit trail
- ✅ Scalable design
- ✅ Complete test coverage
- ✅ No business logic (stays in risk/execution)

Ready for Phase 6: Risk validation layer.
