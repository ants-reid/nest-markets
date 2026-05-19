from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""


# Import models so Alembic sees them.
from app.db import models  # noqa: E402,F401
