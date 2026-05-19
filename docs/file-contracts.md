# File Contracts

## app/main.py
Responsible for:
- FastAPI app creation
- route registration
- startup-safe bootstrap

Must not:
- contain business logic
- read env directly

## app/config.py
Responsible for:
- all environment-backed settings
- typed config
- conservative defaults

Must not:
- contain business logic

## app/logging.py
Responsible for:
- structured logging config

Must not:
- contain app logic

## app/db/base.py
Responsible for:
- SQLAlchemy declarative base

## app/db/session.py
Responsible for:
- database engine
- session factory
- session dependency helpers

## app/api/routes/health.py
Responsible for:
- health endpoint only

Must not:
- contain business logic
