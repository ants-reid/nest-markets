# Market Hunter API - Phase 1 Foundation

This is the Phase 1 backend foundation for the Market Hunter MVP.

## What's included

- **FastAPI** application with clean bootstrap
- **SQLAlchemy 2** database setup with session factory
- **Pydantic 2** configuration management
- **Structured logging** with structlog
- **Health check endpoint** for monitoring
- **Type hints** throughout for IDE support and type safety

## Architecture

```
app/
├── __init__.py
├── main.py              # FastAPI app creation and bootstrap
├── config.py            # Environment-backed settings (Pydantic)
├── logging.py           # Structured logging configuration
├── db/
│   ├── __init__.py
│   ├── base.py          # SQLAlchemy declarative base
│   └── session.py       # Engine, session factory, dependencies
└── api/
    ├── __init__.py
    ├── deps.py          # FastAPI dependency injection helpers
    └── routes/
        ├── __init__.py
        └── health.py    # Health check endpoint
```

## Getting Started

### 1. Install Dependencies

```bash
cd apps/api
pip install poetry
poetry install
```

Or with pip directly:
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

Copy the example env file:
```bash
cp .env.example .env
```

For local development with PostgreSQL, ensure your database is running:
```bash
# Assuming PostgreSQL on localhost:5432
createdb market_hunter
```

### 3. Run the API

```bash
cd apps/api
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or without poetry:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "service": "market-hunter-api"}
```

## Key Design Decisions

- **Config module only**: All environment reads happen in `config.py`
- **Session manager**: Centralized session factory with FastAPI dependency
- **Structured logging**: JSON logs in production, console in development
- **No business logic in routes**: Routes only handle request/response
- **Type hints everywhere**: For IDE support and type safety
- **Conservative defaults**: Safe defaults for database pooling, logging levels, etc.

## Signal Service (Phase 5)

The API includes a signal generation service that orchestrates market features with AI to generate trading signals.

```bash
# Run signal service tests
poetry run pytest tests/services/ -v
```

### Signal Generation

```python
from app.services import SignalService, SignalInput
from app.clients.llm import LLMProviderRouter
from app.config import Settings
from app.db.session import SessionLocal
from datetime import datetime
from uuid import uuid4

# Setup
settings = Settings()
router = LLMProviderRouter(settings)
session = SessionLocal()
service = SignalService(router=router, session=session)

# Generate signal
signal_input = SignalInput(
    asset_id=uuid4(),
    asset_symbol="AAPL",
    current_price=150.0,
    features={"sma_20": 148.0, "rsi_14": 65.0, ...},
    timestamp=datetime.utcnow(),
    macro_context={"fed_rate": 5.5},
    recent_news=[{"headline": "Earnings beat", "sentiment": "positive"}]
)

result = await service.generate_signal(signal_input)
# result.direction: "long", "short", or "flat"
# result.confidence: 0-1 confidence score
# result.catalyst: primary reason for signal
# result.signal_id: persisted to database
```

### What the Signal Service Does

✅ Load active prompts from database
✅ Assemble signal context (features + macro + news)
✅ Call LLM provider with structured schemas
✅ Validate LLM output against schema
✅ Persist signals to database
✅ Comprehensive audit logging

### What It Does NOT Do

❌ Apply risk rules (Phase 6)
❌ Place orders (Phase 7)
❌ Call brokers
❌ Make final decisions (proposes only)

See [SIGNAL_SERVICE.md](SIGNAL_SERVICE.md) for complete reference.

## LLM Provider Layer (Phase 4)

The API includes a provider-agnostic LLM layer for structured AI signal generation.

```bash
# Run LLM client tests
poetry run pytest tests/clients/ -v
```

### LLM Providers

Currently implemented:
- **OpenAI** - GPT-4 with JSON mode and strict schema validation

Future providers:
- Anthropic Claude
- Local LLMs (Ollama, etc.)

### Usage

```python
from app.clients.llm import LLMProviderRouter, LLMRequest
from app.config import Settings

# Initialize router (selects provider from config)
router = LLMProviderRouter(Settings())
provider = router.get_provider()

# Generate structured response
request = LLMRequest(
    system_prompt="You are a trading analyst.",
    user_message="Generate a signal for AAPL at $150.",
    schema={
        "type": "object",
        "properties": {
            "direction": {"type": "string", "enum": ["long", "short", "flat"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1}
        },
        "required": ["direction", "confidence"]
    }
)

response = await provider.generate_structured(request)
# response.content is guaranteed valid JSON matching schema
```

See [LLM_LAYER.md](LLM_LAYER.md) for complete reference and design principles.

### Helpers

Load and validate prompts/schemas separately from providers:

```python
from app.clients.llm.helpers import PromptLoader, SchemaLoader, PromptContext

# Load and render prompt
PromptLoader.validate_prompt(prompt_dict)
user_msg = PromptLoader.render_user_message(template, context)

# Load and validate schema
schema = SchemaLoader.load_schema(json_string_or_dict)
SchemaLoader.validate_schema(schema)

# Build consistent context
context = PromptContext.build_signal_context(
    asset_symbol="AAPL",
    current_price=150.0,
    features={...},
    market_regime="trending_up"
)
```

## Indicators and Features (Phase 3)

The API includes a complete deterministic indicator and feature calculation layer.

```bash
# Run indicator tests
poetry run pytest tests/indicators/ -v

# Run feature tests
poetry run pytest tests/features/ -v
```

See [INDICATORS.md](INDICATORS.md) for complete indicator reference and usage examples.

### Available Indicators

- **EMA**: Exponential Moving Average (trend following)
- **RSI**: Relative Strength Index (overbought/oversold)
- **ATR**: Average True Range (volatility)
- **ADX**: Average Directional Index (trend strength)
- **Volatility**: Realized and Parkinson volatility
- **Spread**: Bid/ask spread quality assessment
- **Trend**: Trend direction and strength scoring
- **Momentum**: ROC and composite momentum scoring
- **Regime**: Market regime classification and quality

### Feature Service

The feature service orchestrates all indicators and produces a `FeatureSnapshot`:

```python
from app.features import calculate_features

features = calculate_features(
    bars=[...],  # OHLCV bars
    quotes=[...],  # Bid/ask quotes
    asset_id="...",
    timestamp=datetime.utcnow()
)
# Returns dict ready for FeatureSnapshot persistence
```

See [INDICATORS.md](INDICATORS.md) for full API reference.

## Database Setup (Phase 2)

The API includes a complete database schema with 20 models:

```bash
# Install dependencies
poetry install

# Run migrations
poetry run alembic upgrade head

# Verify
poetry run alembic current
```

See [DATABASE.md](DATABASE.md) and [MODELS_SUMMARY.md](MODELS_SUMMARY.md) for schema details.

## Database Tables

All 20 Phase 2 tables created with:
- UUID primary keys
- Strategic indexes (~40+ total)
- Foreign key relationships
- Timestamp tracking
- Audit trail support

See [MODELS_SUMMARY.md](MODELS_SUMMARY.md) for complete table reference.

## What's NOT included yet

- Data ingestion services (future)
- Risk validation layer (Phase 6)
- Paper trading execution (Phase 7)
- Live trading (disabled in MVP)

## Testing

Run all tests:

```bash
poetry run pytest tests/ -v
```

## Next Phases

Phase 6 will add:
- Risk validation layer
- Capital allocation
- Position sizing
- Risk rules enforcement

All phases build on this foundation without drifting from architecture.
