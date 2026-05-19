# LLM Provider Layer (Phase 4)

## Overview

Phase 4 implements the **provider-agnostic LLM layer** - the interface between Market Hunter's feature layer and AI signal generation.

This layer is:
- **Provider-agnostic** - Supports any LLM provider (OpenAI, Anthropic, etc.)
- **Structured output focused** - Uses JSON Schema for reliable structured generation
- **Pure interface** - No business logic, no trading logic, no route logic
- **Type-safe** - Full type hints with dataclass return types
- **Async** - All operations are async-first for performance
- **Testable** - Interfaces and contracts are clearly defined

## Architecture

```
Features (Phase 3)
    ↓
[LLM Provider Router] ← Selects active provider from config
    ↓
[LLM Provider Interface] ← Abstracts OpenAI/Anthropic/etc.
    ↓
[LLM Implementation] ← OpenAI for MVP
    ↓
Structured Signal Output → Ready for risk layer
```

## Key Components

### 1. Base Provider Interface (`base.py`)

Abstract interface that all providers must implement:

```python
from app.clients.llm import BaseLLMProvider, LLMRequest, LLMResponse

# All providers implement this
class MyProvider(BaseLLMProvider):
    async def generate_structured(self, request: LLMRequest) -> LLMResponse:
        # Provider-specific implementation
        pass
```

**Request/Response Types:**
- `LLMRequest` - Input: system prompt, user message, JSON schema
- `LLMResponse` - Output: structured content, raw text, model, usage

**Exceptions:**
- `LLMProviderError` - Base provider error
- `LLMValidationError` - Response doesn't match schema
- `LLMTimeoutError` - Request timeout

### 2. OpenAI Provider (`openai_provider.py`)

Production-ready OpenAI implementation using GPT-4 with JSON mode:

```python
from app.clients.llm import OpenAIProvider

provider = OpenAIProvider(
    api_key="sk-...",
    model="gpt-4-turbo",
    timeout=30
)

# Generate structured signal
response = await provider.generate_structured(
    LLMRequest(
        system_prompt="You are a trading analyst.",
        user_message="Generate a signal for AAPL",
        schema={
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["long", "short", "flat"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1}
            },
            "required": ["direction", "confidence"]
        }
    )
)

# Structured output guaranteed to match schema
print(response.content)  # {"direction": "long", "confidence": 0.85}
```

### 3. Router (`router.py`)

Selects the active provider based on configuration:

```python
from app.clients.llm import LLMProviderRouter
from app.config import Settings

settings = Settings()
router = LLMProviderRouter(settings)

provider = router.get_provider()  # Returns configured provider
is_healthy = await router.health_check()  # Check provider availability
```

**Configuration (in `.env`):**
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo
OPENAI_TIMEOUT=30
```

### 4. Helpers (`helpers.py`)

Utilities for working with prompts and schemas (separate from providers):

**PromptLoader** - Load and validate prompts:
```python
from app.clients.llm.helpers import PromptLoader

# Validate prompt has required fields
PromptLoader.validate_prompt(prompt_dict)

# Render user template with context
user_message = PromptLoader.render_user_message(
    template="Analyze {symbol} at price {price}",
    context={"symbol": "AAPL", "price": 150.25}
)
```

**SchemaLoader** - Load and validate schemas:
```python
from app.clients.llm.helpers import SchemaLoader

# Load from JSON string or dict
schema = SchemaLoader.load_schema(json_string_or_dict)

# Validate schema structure
SchemaLoader.validate_schema(schema)

# Extract required fields
required = SchemaLoader.extract_required_fields(schema)
```

**PromptContext** - Build consistent context dicts:
```python
from app.clients.llm.helpers import PromptContext

context = PromptContext.build_signal_context(
    asset_symbol="AAPL",
    current_price=155.0,
    features={
        "sma_20": 150.0,
        "rsi_14": 65.0,
        "trend_direction": "up",
        ...
    },
    recent_bars=[...],
    market_regime="trending_up"
)

# Render user message with context
user_message = PromptLoader.render_user_message(
    template=prompt["user_template"],
    context=context
)
```

## Data Flow Example

### Full Signal Generation Flow

```python
# 1. Get features (Phase 3 output)
features = calculate_features(bars, quotes)

# 2. Load active prompt from database
prompt_version = db.query(PromptVersion).filter(
    PromptVersion.role == "signal_engine",
    PromptVersion.is_active == "active"
).first()

# 3. Build context
context = PromptContext.build_signal_context(
    asset_symbol="AAPL",
    current_price=155.0,
    features=features,
    market_regime="trending_up"
)

# 4. Render prompts
user_message = PromptLoader.render_user_message(
    template=prompt_version.user_template,
    context=context
)

# 5. Load schema
schema = SchemaLoader.load_schema(prompt_version.schema_json)

# 6. Get LLM provider
router = LLMProviderRouter(settings)
provider = router.get_provider()

# 7. Generate structured signal
request = LLMRequest(
    system_prompt=prompt_version.system_prompt,
    user_message=user_message,
    schema=schema,
    temperature=0.5,
    max_tokens=500
)

response = await provider.generate_structured(request)

# 8. Response is guaranteed valid JSON
signal_data = response.content  # {"direction": "long", "confidence": 0.85, ...}

# 9. Create Signal record (Phase 5+)
signal = Signal(
    asset_id=asset.id,
    prompt_version_id=prompt_version.id,
    direction=signal_data["direction"],
    confidence=signal_data["confidence"],
    structured_output=json.dumps(signal_data),
    ...
)
db.session.add(signal)
```

## JSON Schema Design

The layer uses strict JSON Schema validation. Prompts must define schemas for reliable generation:

### Example Schema for Trading Signal

```json
{
  "type": "object",
  "properties": {
    "direction": {
      "type": "string",
      "enum": ["long", "short", "flat"],
      "description": "Trade direction"
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Confidence 0-1"
    },
    "catalyst": {
      "type": "string",
      "description": "Primary reason for signal"
    },
    "entry_price": {
      "type": "number",
      "description": "Suggested entry price"
    },
    "stop_loss": {
      "type": "number",
      "description": "Suggested stop loss price"
    },
    "risk_reward_ratio": {
      "type": "number",
      "minimum": 0
    },
    "reasoning": {
      "type": "string",
      "description": "Detailed explanation"
    }
  },
  "required": ["direction", "confidence", "catalyst", "entry_price", "stop_loss"]
}
```

## Testing

Comprehensive test coverage includes:

### Unit Tests
```bash
# All tests
poetry run pytest tests/clients/ -v

# Specific test files
poetry run pytest tests/clients/llm_provider_test.py -v
poetry run pytest tests/clients/llm_router_test.py -v
poetry run pytest tests/clients/llm_helpers_test.py -v
```

### Test Coverage
- Provider interface abstract methods
- OpenAI implementation with mock responses
- Schema validation (type checking, required fields)
- Error handling (invalid JSON, timeouts)
- Router provider selection
- Helper utilities (prompts, schemas, context)

## Design Principles Applied

✅ **No business logic** - Only marshalling requests/responses

✅ **Provider-agnostic** - Interface supports any LLM provider

✅ **Structured outputs** - JSON Schema validation ensures valid responses

✅ **Type safety** - Dataclasses for requests/responses, full type hints

✅ **Async-first** - All operations async for performance

✅ **Separation of concerns** - Providers separate from helpers

✅ **Configuration-driven** - Active provider selected via settings

✅ **Error handling** - Specific exceptions for different failures

## Adding New Providers

To add a new provider (e.g., Anthropic):

1. Create `app/clients/llm/anthropic_provider.py`
2. Implement `BaseLLMProvider` interface
3. Add config settings to `app/config.py`
4. Update `app/clients/llm/router.py` to instantiate new provider
5. Add tests in `tests/clients/llm_provider_test.py`

```python
# app/clients/llm/anthropic_provider.py
class AnthropicProvider(BaseLLMProvider):
    async def generate_structured(self, request: LLMRequest) -> LLMResponse:
        # Anthropic-specific implementation
        pass
```

Then in `.env`:
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=...
```

## API Reference

### LLMRequest

```python
LLMRequest(
    system_prompt: str,        # System message establishing role
    user_message: str,         # User-facing message
    schema: dict[str, Any],    # JSON Schema for output
    temperature: float = 0.7,  # 0=deterministic, 1=creative
    max_tokens: Optional[int] = None,  # Max response tokens
    timeout: Optional[int] = None      # Request timeout
)
```

### LLMResponse

```python
LLMResponse(
    content: dict[str, Any],         # Structured response (validated)
    raw_text: str,                   # Raw response text
    model: str,                      # Model used
    stop_reason: str,                # Why it stopped
    usage_tokens: Optional[dict] = None  # Token usage stats
)
```

### BaseLLMProvider

```python
class BaseLLMProvider(ABC):
    async def generate_structured(self, request: LLMRequest) -> LLMResponse:
        """Generate structured response matching schema."""
        pass
    
    async def health_check(self) -> bool:
        """Check if provider is available."""
        pass
```

## What's NOT included

- Business logic (belongs in signal service)
- Trading decisions (belong in signal/risk layer)
- Route handlers (belong in API layer)
- Broker integration (belongs in execution layer)
- Database operations (belong in services using this layer)

## Next Phases

**Phase 5: Signal Service**
- Consumes features (Phase 3) and prompts (database)
- Uses LLM provider (Phase 4)
- Generates trading signals
- Outputs ready for risk layer

**Phase 6: Risk and Execution**
- Risk rules validation
- Paper execution
- Live execution (if enabled)

This phase provides the foundation for AI-powered signal generation.

## Configuration Example

Complete `.env` setup:

```
# App
APP_NAME=Market Hunter API
APP_VERSION=0.1.0
DEBUG=false

# Database
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/market_hunter
DATABASE_ECHO=false

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# LLM
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4-turbo
OPENAI_TIMEOUT=30
```

## Troubleshooting

### Invalid API Key
```
LLMProviderError: OpenAI API key is required
```
Set `OPENAI_API_KEY` in `.env`

### Schema Validation Failed
```
LLMValidationError: Missing required property: direction
```
Check that your JSON schema matches the LLM's response format

### Timeout Errors
```
LLMTimeoutError: OpenAI request timed out
```
Increase `OPENAI_TIMEOUT` or check network connection

### Provider Not Found
```
LLMProviderError: Unsupported LLM provider: unsupported_provider
```
Check `LLM_PROVIDER` setting - MVP supports 'openai' only
