# Coding Rules

## Global rules
- Use Python 3.12
- Use type hints everywhere
- Use Pydantic 2 for settings and schemas
- Use SQLAlchemy 2 patterns
- Keep modules small and single-purpose
- Prefer explicitness over cleverness
- Use clear names
- No circular imports
- No silent exception swallowing
- Every public method must have a short docstring
- Every service must be testable

## Layer rules
- Route files handle request/response only
- Service files hold business logic
- Provider adapters wrap external services only
- DB models live only in the db/model layer
- Indicators are deterministic and side-effect free

## Forbidden
- direct environment reads outside config.py
- direct broker calls outside broker adapters
- direct AI calls outside LLM providers
- business logic in React components
- hidden global state
- placeholder abstractions with no purpose

## Required
- structured logging
- explicit config
- audit-friendly behaviour
- clear error messages
- conservative defaults
