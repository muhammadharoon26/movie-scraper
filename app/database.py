"""Database engine and session factory.

Provides a synchronous SQLModel engine and a session generator for FastAPI dependency injection.
"""

from sqlmodel import Session, create_engine

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


def get_session():
    """Yield a database session scoped to the request lifecycle."""
    with Session(engine) as session:
        yield session
