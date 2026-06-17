"""Movie CRUD routes with JWT protection and soft delete."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.database import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas import MovieListResponse, MovieRead, MovieUpdate
from app.services import get_movie_by_id, list_movies, soft_delete_movie, update_movie

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get(
    "", response_model=MovieListResponse, summary="List all movies with pagination"
)
def get_movies(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return a paginated list of active (non-deleted) movies."""
    return list_movies(session, page=page, limit=limit)


@router.get("/{movie_id}", response_model=MovieRead, summary="Get a single movie by ID")
def get_movie(
    movie_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Fetch a movie by UUID. Returns 404 if not found or soft-deleted."""
    movie = get_movie_by_id(session, movie_id)
    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    return MovieRead.model_validate(movie)


@router.patch(
    "/{movie_id}", response_model=MovieRead, summary="Update a movie's title or genres"
)
def patch_movie(
    movie_id: uuid.UUID,
    body: MovieUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Partially update a movie. Only title and genres are modifiable."""
    movie = update_movie(session, movie_id, body)
    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    return MovieRead.model_validate(movie)


@router.delete(
    "/{movie_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft-delete a movie"
)
def delete_movie(
    movie_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a movie by setting deleted_at. Returns 404 if not found."""
    if not soft_delete_movie(session, movie_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    return None
