"""Business logic — auth and movie CRUD services."""

import math
import uuid
from datetime import datetime, timezone

from sqlmodel import Session, col, func, select

from app.models import Movie, User
from app.schemas import (
    MovieListResponse,
    MovieRead,
    MovieUpdate,
    PaginationMeta,
    TokenResponse,
)
from app.security import create_access_token, hash_password, verify_password


# ── Auth ──────────────────────────────────────────────────


def authenticate_user(
    session: Session, username: str, password: str
) -> TokenResponse | None:
    """Verify credentials and return a TokenResponse, or None on failure.

    Performs a constant-time password check even on non-existent users
    to mitigate timing-based username enumeration.
    """
    user = session.exec(select(User).where(User.username == username)).first()

    if user is None:
        verify_password(password, hash_password("dummy"))
        return None

    if not verify_password(password, user.hashed_password):
        return None

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


def register_user(session: Session, username: str, password: str) -> User:
    """Create a new user with a hashed password.

    Raises sqlalchemy.exc.IntegrityError if the username already exists.
    """
    user = User(username=username, hashed_password=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_by_username(session: Session, username: str) -> User | None:
    """Look up a user by username."""
    return session.exec(select(User).where(User.username == username)).first()


# ── Movies ────────────────────────────────────────────────


def _active_filter():
    """Base filter for non-deleted movies."""
    return Movie.deleted_at.is_(None)  # type: ignore[union-attr]


def list_movies(session: Session, page: int = 1, limit: int = 20) -> MovieListResponse:
    """Return a paginated list of active (non-deleted) movies."""
    total = session.exec(
        select(func.count()).select_from(Movie).where(_active_filter())
    ).one()
    total_pages = math.ceil(total / limit) if total > 0 else 0
    offset = (page - 1) * limit

    movies = session.exec(
        select(Movie)
        .where(_active_filter())
        .order_by(col(Movie.created_at).desc())
        .offset(offset)
        .limit(limit)
    ).all()

    return MovieListResponse(
        data=[MovieRead.model_validate(m) for m in movies],
        meta=PaginationMeta(
            page=page, limit=limit, total=total, total_pages=total_pages
        ),
    )


def get_movie_by_id(session: Session, movie_id: uuid.UUID) -> Movie | None:
    """Fetch a single active movie by UUID, or None if not found / soft-deleted."""
    return session.exec(
        select(Movie).where(Movie.id == movie_id, _active_filter())
    ).first()


def update_movie(
    session: Session, movie_id: uuid.UUID, data: MovieUpdate
) -> Movie | None:
    """Partially update an active movie's title and/or genres."""
    movie = get_movie_by_id(session, movie_id)
    if movie is None:
        return None

    if data.title is not None:
        movie.title = data.title
    if data.genres is not None:
        movie.genres = data.genres

    movie.updated_at = datetime.now(timezone.utc)
    session.add(movie)
    session.commit()
    session.refresh(movie)
    return movie


def soft_delete_movie(session: Session, movie_id: uuid.UUID) -> bool:
    """Delete a movie from the database. Returns True if found and deleted."""
    movie = get_movie_by_id(session, movie_id)
    if movie is None:
        return False

    session.delete(movie)
    session.commit()
    return True
