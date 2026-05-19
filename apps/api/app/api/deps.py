"""FastAPI dependency injection helpers."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session


def get_db() -> Generator[Session, None, None]:
	"""FastAPI dependency for database sessions."""
	yield from get_db_session()

# Annotated type for database session dependency
SessionDep = Annotated[Session, Depends(get_db)]
