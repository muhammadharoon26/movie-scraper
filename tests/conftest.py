"""Shared test fixtures — DB isolation, TestClient, and auth helpers."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

# Override DATABASE_URL before app imports
_test_db_url = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/movie_scraper_test",
    ),
)
os.environ["DATABASE_URL"] = _test_db_url

from app.database import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Movie, ScrapeLog, User  # noqa: E402, F401
from app.security import hash_password  # noqa: E402

_engine = create_engine(_test_db_url, echo=False, pool_pre_ping=True)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    SQLModel.metadata.create_all(_engine)
    yield
    SQLModel.metadata.drop_all(_engine)


@pytest.fixture()
def db_session():
    connection = _engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session):
    def _override():
        yield db_session

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def test_user(db_session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        username=f"testuser_{uuid.uuid4().hex[:8]}",
        hashed_password=hash_password("testpassword123"),
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def auth_headers(client: TestClient, test_user: User) -> dict[str, str]:
    resp = client.post(
        "/auth/login",
        json={"username": test_user.username, "password": "testpassword123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Factory helpers ───────────────────────────────────────


def make_movie(
    session: Session, title: str = "Test Movie", tmdb_id: int | None = None, **kwargs
) -> Movie:
    """Create and flush a Movie with sensible defaults."""
    _tmdb_id = tmdb_id if tmdb_id is not None else abs(hash(uuid.uuid4())) % 1_000_000
    movie = Movie(
        id=uuid.uuid4(),
        title=title,
        tmdb_id=_tmdb_id,
        genres=kwargs.get("genres", ["Action", "Drama"]),
        release_year=kwargs.get("release_year", 2026),
        media_type=kwargs.get("media_type", "movie"),
        thumbnail_url=kwargs.get(
            "thumbnail_url", "https://image.tmdb.org/t/p/w500/test.jpg"
        ),
        source_url=kwargs.get(
            "source_url", f"https://www.themoviedb.org/movie/{_tmdb_id}"
        ),
    )
    session.add(movie)
    session.flush()
    return movie


def make_scrape_log(session: Session, status: str = "success", **kwargs) -> ScrapeLog:
    """Create and flush a ScrapeLog with sensible defaults."""
    from datetime import datetime, timezone

    log = ScrapeLog(
        id=uuid.uuid4(),
        started_at=kwargs.get("started_at", datetime.now(timezone.utc)),
        finished_at=kwargs.get("finished_at", datetime.now(timezone.utc)),
        total_fetched=kwargs.get("total_fetched", 20),
        new_inserted=kwargs.get("new_inserted", 18),
        duplicates_skipped=kwargs.get("duplicates_skipped", 2),
        status=status,
    )
    session.add(log)
    session.flush()
    return log
