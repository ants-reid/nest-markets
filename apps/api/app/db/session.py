from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,  # Recycle connections after 30 min to avoid stale connections
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    class_=Session,
)


def ensure_public_search_path(session: Session) -> None:
    """Normalize PostgreSQL schema lookup for pooled connections."""
    bind = session.get_bind()
    if bind is not None and bind.dialect.name.startswith("postgresql"):
        session.execute(text("SET search_path TO public"))


def get_db_session() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed."""
    db = SessionLocal()
    try:
        ensure_public_search_path(db)
        yield db
    finally:
        db.close()
